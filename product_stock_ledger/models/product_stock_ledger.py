from odoo import models, fields, api, tools
from odoo.exceptions import UserError


class ProductStockLedger(models.Model):
    """
    SQL-backed read-only model that flattens stock.move.line records
    into a ledger format with running balance per (product, warehouse).
    Compatible with Odoo 19 CE (price_unit removed from stock.move).
    """
    _name = 'product.stock.ledger'
    _description = 'Product Stock Ledger'
    _auto = False          # do NOT create a real table; we use a SQL view
    _order = 'product_id, date, id'

    # ── Core identifiers ──────────────────────────────────────────────
    product_id      = fields.Many2one('product.product',    string='Product',       readonly=True)
    warehouse_id    = fields.Many2one('stock.warehouse',    string='Warehouse',     readonly=True)

    # ── Movement info ─────────────────────────────────────────────────
    date            = fields.Datetime(string='Date',        readonly=True)
    voucher         = fields.Char(string='Voucher',         readonly=True,
                                  help='Source document reference (PO, SO, Transfer, etc.)')
    particulars     = fields.Char(string='Particulars',     readonly=True,
                                  help='Origin / description of the movement')
    move_type       = fields.Char(string='Type',            readonly=True,
                                  help='IN / OUT / INT (internal)')

    # ── Quantity & Rate columns ───────────────────────────────────────
    rec_qty         = fields.Float(string='Rec. Qty',       readonly=True, digits=(16, 4))
    rec_rate        = fields.Float(string='Rec. Rate',      readonly=True, digits=(16, 4))
    issue_qty       = fields.Float(string='Issue Qty',      readonly=True, digits=(16, 4))
    issue_rate      = fields.Float(string='Issue Rate',     readonly=True, digits=(16, 4))
    balance         = fields.Float(string='Balance',        readonly=True, digits=(16, 4),
                                   help='Running stock balance (cumulative per product/warehouse)')

    # ── Unit & Status ─────────────────────────────────────────────────
    uom             = fields.Char(string='Unit',            readonly=True)
    invoice_status  = fields.Char(string='Invoice Status',  readonly=True)

    # ── Hidden helpers ────────────────────────────────────────────────
    move_id         = fields.Many2one('stock.move',         string='Stock Move',    readonly=True)
    company_id      = fields.Many2one('res.company',        string='Company',       readonly=True)

    # ------------------------------------------------------------------
    def init(self):
        """Drop and re-create the database view."""
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
CREATE OR REPLACE VIEW product_stock_ledger AS

WITH
-- 1. Resolve each internal location to its warehouse
loc_warehouse AS (
    SELECT
        sl.id        AS location_id,
        sw.id        AS warehouse_id
    FROM stock_location sl
    JOIN stock_warehouse sw
        ON sl.complete_name LIKE sw.code || '%'
        OR sl.id = sw.lot_stock_id
    WHERE sl.usage = 'internal'
),

-- 2. Unit cost per move from the stock valuation layer
move_cost AS (
    SELECT
        stock_move_id,
        CASE
            WHEN SUM(ABS(quantity)) > 0
            THEN SUM(ABS(value)) / SUM(ABS(quantity))
            ELSE 0
        END AS unit_cost
    FROM stock_valuation_layer
    GROUP BY stock_move_id
)

SELECT
    sml.id                                              AS id,
    sml.product_id                                      AS product_id,
    COALESCE(wh_src.warehouse_id, wh_dest.warehouse_id) AS warehouse_id,
    sm.date                                             AS date,
    COALESCE(so.name, po.name, sp.name, sm.origin)      AS voucher,
    COALESCE(sm.origin, sp.name, sp.reference)          AS particulars,

    CASE
        WHEN src_loc.usage = 'supplier'                            THEN 'IN'
        WHEN dest_loc.usage = 'customer'                           THEN 'OUT'
        WHEN src_loc.usage = 'customer'                            THEN 'IN'
        WHEN dest_loc.usage = 'supplier'                           THEN 'OUT'
        WHEN src_loc.usage IN ('internal','transit')
         AND dest_loc.usage IN ('internal','transit')              THEN 'INT'
        WHEN dest_loc.usage = 'internal'                           THEN 'IN'
        WHEN src_loc.usage = 'internal'                            THEN 'OUT'
        ELSE 'INT'
    END                                                 AS move_type,

    -- Received Qty
    CASE
        WHEN dest_loc.usage = 'internal' AND src_loc.usage != 'internal'
            THEN sml.quantity
        WHEN src_loc.usage = 'customer'
            THEN sml.quantity
        ELSE 0
    END                                                 AS rec_qty,

    -- Received Rate
    CASE
        WHEN dest_loc.usage = 'internal' AND src_loc.usage != 'internal'
            THEN COALESCE(mc.unit_cost, 0)
        WHEN src_loc.usage = 'customer'
            THEN COALESCE(mc.unit_cost, 0)
        ELSE 0
    END                                                 AS rec_rate,

    -- Issue Qty
    CASE
        WHEN src_loc.usage = 'internal' AND dest_loc.usage != 'internal'
            THEN sml.quantity
        ELSE 0
    END                                                 AS issue_qty,

    -- Issue Rate
    CASE
        WHEN src_loc.usage = 'internal' AND dest_loc.usage != 'internal'
            THEN COALESCE(mc.unit_cost, 0)
        ELSE 0
    END                                                 AS issue_rate,

    -- Running balance window function
    SUM(
        CASE
            WHEN dest_loc.usage = 'internal' AND src_loc.usage != 'internal'
                THEN  sml.quantity
            WHEN src_loc.usage = 'customer'
                THEN  sml.quantity
            WHEN src_loc.usage = 'internal' AND dest_loc.usage != 'internal'
                THEN -sml.quantity
            ELSE 0
        END
    ) OVER (
        PARTITION BY sml.product_id,
                     COALESCE(wh_src.warehouse_id, wh_dest.warehouse_id)
        ORDER BY sm.date, sml.id
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    )                                                   AS balance,

    uom_u.name                                          AS uom,

    CASE
        WHEN so.id IS NOT NULL THEN so.invoice_status
        WHEN po.id IS NOT NULL THEN po.invoice_status
        ELSE NULL
    END                                                 AS invoice_status,

    sm.id           AS move_id,
    sm.company_id   AS company_id

FROM stock_move_line sml

JOIN stock_move sm
    ON sm.id    = sml.move_id
   AND sm.state = 'done'

JOIN stock_location src_loc
    ON src_loc.id = sml.location_id

JOIN stock_location dest_loc
    ON dest_loc.id = sml.location_dest_id

LEFT JOIN loc_warehouse wh_src
    ON wh_src.location_id = sml.location_id
   AND src_loc.usage = 'internal'

LEFT JOIN loc_warehouse wh_dest
    ON wh_dest.location_id = sml.location_dest_id
   AND dest_loc.usage = 'internal'

LEFT JOIN uom_uom uom_u
    ON uom_u.id = sml.product_uom_id

LEFT JOIN stock_picking sp
    ON sp.id = sml.picking_id

LEFT JOIN move_cost mc
    ON mc.stock_move_id = sm.id

LEFT JOIN sale_order so
    ON so.name = sm.origin

LEFT JOIN purchase_order po
    ON po.name = sm.origin

WHERE sm.state = 'done'
;
        """)

    def write(self, vals):
        raise UserError('Stock Ledger records are read-only.')

    def create(self, vals):
        raise UserError('Stock Ledger records are read-only.')

    def unlink(self):
        raise UserError('Stock Ledger records are read-only.')
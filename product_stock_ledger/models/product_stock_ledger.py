from odoo import models, fields, api, tools
from odoo.exceptions import UserError


class ProductStockLedger(models.Model):
    """
    SQL-backed read-only model that flattens stock.move.line records
    into a ledger format with running balance per (product, warehouse).
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

    # ── Hidden helpers for grouping / filtering ───────────────────────
    move_id         = fields.Many2one('stock.move',         string='Stock Move',    readonly=True)
    company_id      = fields.Many2one('res.company',        string='Company',       readonly=True)

    # ------------------------------------------------------------------
    def init(self):
        """Drop and re-create the database view."""
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
CREATE OR REPLACE VIEW product_stock_ledger AS
SELECT
    sml.id                              AS id,
    sml.product_id                      AS product_id,

    -- Resolve the warehouse from the source or destination location
    COALESCE(wh_src.id, wh_dest.id)    AS warehouse_id,

    sm.date                             AS date,

    -- Voucher: prefer SO/PO name, fallback to picking name, then move origin
    COALESCE(
        so.name,
        po.name,
        sp.name,
        sm.origin
    )                                   AS voucher,

    -- Particulars: human-readable description
    COALESCE(sm.origin, sp.name, sm.name)
                                        AS particulars,

    -- Move type classification
    CASE
        WHEN src_usage.usage = 'supplier'                       THEN 'IN'
        WHEN dest_usage.usage = 'customer'                      THEN 'OUT'
        WHEN src_usage.usage = 'customer'                       THEN 'IN'   -- return
        WHEN dest_usage.usage = 'supplier'                      THEN 'OUT'  -- return
        WHEN src_usage.usage IN ('internal','transit')
         AND dest_usage.usage IN ('internal','transit')         THEN 'INT'
        WHEN dest_usage.usage = 'internal'                      THEN 'IN'
        WHEN src_usage.usage = 'internal'                       THEN 'OUT'
        ELSE 'INT'
    END                                 AS move_type,

    -- Received quantity (incoming to internal locations)
    CASE
        WHEN dest_usage.usage = 'internal'
         AND src_usage.usage  != 'internal'
            THEN sml.quantity
        WHEN src_usage.usage = 'customer'           -- customer return
            THEN sml.quantity
        ELSE 0
    END                                 AS rec_qty,

    -- Received rate = unit cost at time of move
    CASE
        WHEN dest_usage.usage = 'internal'
         AND src_usage.usage  != 'internal'
            THEN COALESCE(sm.price_unit, 0)
        ELSE 0
    END                                 AS rec_rate,

    -- Issued quantity (leaving internal locations)
    CASE
        WHEN src_usage.usage = 'internal'
         AND dest_usage.usage != 'internal'
            THEN sml.quantity
        WHEN dest_usage.usage = 'customer' AND src_usage.usage = 'internal'
            THEN sml.quantity
        ELSE 0
    END                                 AS issue_qty,

    -- Issue rate
    CASE
        WHEN src_usage.usage = 'internal'
         AND dest_usage.usage != 'internal'
            THEN COALESCE(sm.price_unit, 0)
        ELSE 0
    END                                 AS issue_rate,

    -- Running balance using a window function
    SUM(
        CASE
            WHEN dest_usage.usage = 'internal'
             AND src_usage.usage  != 'internal'
                THEN sml.quantity
            WHEN src_usage.usage = 'customer'
                THEN sml.quantity
            WHEN src_usage.usage = 'internal'
             AND dest_usage.usage != 'internal'
                THEN -sml.quantity
            ELSE 0
        END
    ) OVER (
        PARTITION BY sml.product_id, COALESCE(wh_src.id, wh_dest.id)
        ORDER BY sm.date, sml.id
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    )                                   AS balance,

    -- Unit of measure name
    uom.name                            AS uom,

    -- Invoice status from linked SO or PO (if any)
    CASE
        WHEN so.id IS NOT NULL  THEN so.invoice_status
        WHEN po.id IS NOT NULL  THEN po.invoice_status
        ELSE NULL
    END                                 AS invoice_status,

    sm.id                               AS move_id,
    sm.company_id                       AS company_id

FROM stock_move_line  sml

-- Parent stock move
JOIN stock_move sm
    ON sm.id = sml.move_id
   AND sm.state = 'done'

-- Source & destination location details
JOIN stock_location src_loc
    ON src_loc.id = sml.location_id
JOIN stock_location dest_loc
    ON dest_loc.id = sml.location_dest_id

-- Location usages (via usage field on stock.location)
JOIN (SELECT id, usage FROM stock_location) src_usage
    ON src_usage.id = sml.location_id
JOIN (SELECT id, usage FROM stock_location) dest_usage
    ON dest_usage.id = sml.location_dest_id

-- Warehouse from source location
LEFT JOIN stock_warehouse wh_src
    ON wh_src.lot_stock_id IN (
        SELECT id FROM stock_location
        WHERE complete_name LIKE '%' || (
            SELECT name FROM stock_location WHERE id = src_loc.id
        ) || '%'
        OR id = src_loc.id
    )
   AND src_usage.usage = 'internal'

-- Warehouse from destination location
LEFT JOIN stock_warehouse wh_dest
    ON wh_dest.lot_stock_id IN (
        SELECT id FROM stock_location
        WHERE complete_name LIKE '%' || (
            SELECT name FROM stock_location WHERE id = dest_loc.id
        ) || '%'
        OR id = dest_loc.id
    )
   AND dest_usage.usage = 'internal'

-- Unit of measure
LEFT JOIN uom_uom uom
    ON uom.id = sml.product_uom_id

-- Picking
LEFT JOIN stock_picking sp
    ON sp.id = sml.picking_id

-- Sale order (via picking or move origin)
LEFT JOIN sale_order so
    ON so.name = sm.origin

-- Purchase order
LEFT JOIN purchase_order po
    ON po.name = sm.origin

WHERE
    sm.state = 'done'
;
        """)

    # ------------------------------------------------------------------
    # Prevent write operations on this read-only view
    # ------------------------------------------------------------------
    def write(self, vals):
        raise UserError('Stock Ledger records are read-only.')

    def create(self, vals):
        raise UserError('Stock Ledger records are read-only.')

    def unlink(self):
        raise UserError('Stock Ledger records are read-only.')

from odoo import models, fields, tools
from odoo.exceptions import UserError


class ProductStockLedger(models.Model):
    """
    SQL-backed read-only model (PostgreSQL VIEW).
    Compatible with Odoo 19 CE with or without stock_account / OdooMates accounting.
    Detects available tables/columns at install time and builds the VIEW accordingly.
    """
    _name = 'product.stock.ledger'
    _description = 'Product Stock Ledger'
    _auto = False
    _order = 'product_id, date, id'

    product_id      = fields.Many2one('product.product', string='Product',         readonly=True)
    warehouse_id    = fields.Many2one('stock.warehouse',  string='Warehouse',       readonly=True)
    date            = fields.Datetime(string='Date',      readonly=True)
    voucher         = fields.Char(string='Voucher',       readonly=True)
    particulars     = fields.Char(string='Particulars',   readonly=True)
    move_type       = fields.Char(string='Type',          readonly=True)
    rec_qty         = fields.Float(string='Rec. Qty',     readonly=True, digits=(16, 4))
    rec_rate        = fields.Float(string='Rec. Rate',    readonly=True, digits=(16, 4))
    issue_qty       = fields.Float(string='Issue Qty',    readonly=True, digits=(16, 4))
    issue_rate      = fields.Float(string='Issue Rate',   readonly=True, digits=(16, 4))
    balance         = fields.Float(string='Balance',      readonly=True, digits=(16, 4))
    uom             = fields.Char(string='Unit',          readonly=True)
    invoice_status  = fields.Char(string='Invoice Status', readonly=True)
    move_id         = fields.Many2one('stock.move',       string='Stock Move',      readonly=True)
    company_id      = fields.Many2one('res.company',      string='Company',         readonly=True)

    # ------------------------------------------------------------------
    def _table_exists(self, table_name):
        self.env.cr.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = %s
            )
        """, (table_name,))
        return self.env.cr.fetchone()[0]

    def _col_exists(self, table_name, col_name):
        self.env.cr.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name   = %s
                  AND column_name  = %s
            )
        """, (table_name, col_name))
        return self.env.cr.fetchone()[0]

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)

        # ── Detect optional tables ────────────────────────────────────
        has_svl  = self._table_exists('stock_valuation_layer')
        has_so   = self._table_exists('sale_order')
        has_po   = self._table_exists('purchase_order')

        # ── Detect safe fallback columns ─────────────────────────────
        # stock_move.reference exists in Odoo 17+
        sm_ref   = 'sm.reference' if self._col_exists('stock_move', 'reference') else 'sm.origin'
        # sale_order.invoice_status
        so_inv   = 'so.invoice_status' if has_so and self._col_exists('sale_order', 'invoice_status') else "NULL::varchar"
        # purchase_order.invoice_status
        po_inv   = 'po.invoice_status' if has_po and self._col_exists('purchase_order', 'invoice_status') else "NULL::varchar"

        # ── Cost CTE (stock_valuation_layer when available) ───────────
        if has_svl:
            cost_cte = """
move_cost AS (
    SELECT
        stock_move_id,
        CASE WHEN SUM(ABS(quantity)) > 0
             THEN SUM(ABS(value)) / SUM(ABS(quantity))
             ELSE 0
        END AS unit_cost
    FROM stock_valuation_layer
    WHERE stock_move_id IS NOT NULL
    GROUP BY stock_move_id
),"""
            cost_join  = "LEFT JOIN move_cost mc ON mc.stock_move_id = sm.id"
            cost_field = "COALESCE(mc.unit_cost, 0)"
        else:
            cost_cte   = ""
            cost_join  = ""
            cost_field = "0::numeric"

        # ── Sale order fragments ──────────────────────────────────────
        if has_so:
            so_join = "LEFT JOIN sale_order so ON so.name = sm.origin"
            so_name = "so.name"
            so_cond = "so.id IS NOT NULL"
        else:
            so_join = ""
            so_name = "NULL::varchar"
            so_cond = "FALSE"

        # ── Purchase order fragments ──────────────────────────────────
        if has_po:
            po_join = "LEFT JOIN purchase_order po ON po.name = sm.origin"
            po_name = "po.name"
            po_cond = "po.id IS NOT NULL"
        else:
            po_join = ""
            po_name = "NULL::varchar"
            po_cond = "FALSE"

        sql = f"""
CREATE OR REPLACE VIEW product_stock_ledger AS

WITH
-- 1. Map every internal location to its warehouse (distinct to avoid duplicate rows)
loc_warehouse AS (
    SELECT DISTINCT ON (sl.id)
        sl.id AS location_id,
        sw.id AS warehouse_id
    FROM stock_location sl
    JOIN stock_warehouse sw
        ON sl.id = sw.lot_stock_id
        OR sl.complete_name LIKE (
            SELECT complete_name || '/%'
            FROM stock_location root
            WHERE root.id = sw.lot_stock_id
        )
    WHERE sl.usage = 'internal'
    ORDER BY sl.id, sw.id
),
{cost_cte}

-- 2. Main ledger
ledger AS (
    SELECT
        sml.id                                               AS id,
        sml.product_id                                       AS product_id,
        COALESCE(wh_src.warehouse_id, wh_dest.warehouse_id) AS warehouse_id,
        sm.date                                              AS date,

        -- Voucher: SO name → PO name → picking name → move origin/reference
        COALESCE({so_name}, {po_name}, sp.name, sm.origin, {sm_ref}, '')
                                                             AS voucher,

        -- Particulars: move origin → move reference → picking name
        COALESCE(sm.origin, {sm_ref}, sp.name, '')            AS particulars,

        -- Movement type
        CASE
            WHEN src_loc.usage = 'supplier'                          THEN 'IN'
            WHEN dest_loc.usage = 'customer'                         THEN 'OUT'
            WHEN src_loc.usage = 'customer'                          THEN 'IN'
            WHEN dest_loc.usage = 'supplier'                         THEN 'OUT'
            WHEN src_loc.usage  IN ('internal','transit')
             AND dest_loc.usage IN ('internal','transit')            THEN 'INT'
            WHEN dest_loc.usage = 'internal'                         THEN 'IN'
            WHEN src_loc.usage  = 'internal'                         THEN 'OUT'
            ELSE 'INT'
        END                                                  AS move_type,

        -- Received qty
        CASE
            WHEN dest_loc.usage = 'internal' AND src_loc.usage != 'internal'
                THEN sml.quantity
            WHEN src_loc.usage = 'customer'
                THEN sml.quantity
            ELSE 0
        END                                                  AS rec_qty,

        -- Received rate
        CASE
            WHEN dest_loc.usage = 'internal' AND src_loc.usage != 'internal'
                THEN {cost_field}
            WHEN src_loc.usage = 'customer'
                THEN {cost_field}
            ELSE 0
        END                                                  AS rec_rate,

        -- Issue qty
        CASE
            WHEN src_loc.usage = 'internal' AND dest_loc.usage != 'internal'
                THEN sml.quantity
            ELSE 0
        END                                                  AS issue_qty,

        -- Issue rate
        CASE
            WHEN src_loc.usage = 'internal' AND dest_loc.usage != 'internal'
                THEN {cost_field}
            ELSE 0
        END                                                  AS issue_rate,

        -- Running balance per product + warehouse
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
        )                                                    AS balance,

        COALESCE(uom_u.name, '')                             AS uom,

        -- Invoice status from SO or PO
        COALESCE(CASE
            WHEN {so_cond} THEN {so_inv}
            WHEN {po_cond} THEN {po_inv}
            ELSE NULL
        END, '')                                             AS invoice_status,

        sm.id         AS move_id,
        sm.company_id AS company_id

    FROM stock_move_line sml

    JOIN stock_move sm
        ON sm.id    = sml.move_id
       AND sm.state = 'done'

    JOIN stock_location src_loc  ON src_loc.id  = sml.location_id
    JOIN stock_location dest_loc ON dest_loc.id = sml.location_dest_id

    LEFT JOIN loc_warehouse wh_src
        ON wh_src.location_id = sml.location_id
       AND src_loc.usage = 'internal'

    LEFT JOIN loc_warehouse wh_dest
        ON wh_dest.location_id = sml.location_dest_id
       AND dest_loc.usage = 'internal'

    LEFT JOIN uom_uom    uom_u ON uom_u.id = sml.product_uom_id
    LEFT JOIN stock_picking sp ON sp.id    = sml.picking_id

    {cost_join}
    {so_join}
    {po_join}

    WHERE sm.state = 'done'
)

SELECT * FROM ledger
;
        """

        self.env.cr.execute(sql)

    # ------------------------------------------------------------------
    def write(self, vals):
        raise UserError('Stock Ledger records are read-only.')

    def create(self, vals):
        raise UserError('Stock Ledger records are read-only.')

    def unlink(self):
        raise UserError('Stock Ledger records are read-only.')











# from odoo import models, fields, tools
# from odoo.exceptions import UserError
#
#
# class ProductStockLedger(models.Model):
#     """
#     SQL-backed read-only model (PostgreSQL VIEW).
#     Compatible with Odoo 19 CE with or without stock_account / OdooMates accounting.
#     Detects available tables/columns at install time and builds the VIEW accordingly.
#     """
#     _name = 'product.stock.ledger'
#     _description = 'Product Stock Ledger'
#     _auto = False
#     _order = 'product_id, date, id'
#
#     product_id      = fields.Many2one('product.product', string='Product',         readonly=True)
#     warehouse_id    = fields.Many2one('stock.warehouse',  string='Warehouse',       readonly=True)
#     date            = fields.Datetime(string='Date',      readonly=True)
#     voucher         = fields.Char(string='Voucher',       readonly=True)
#     particulars     = fields.Char(string='Particulars',   readonly=True)
#     move_type       = fields.Char(string='Type',          readonly=True)
#     rec_qty         = fields.Float(string='Rec. Qty',     readonly=True, digits=(16, 4))
#     rec_rate        = fields.Float(string='Rec. Rate',    readonly=True, digits=(16, 4))
#     issue_qty       = fields.Float(string='Issue Qty',    readonly=True, digits=(16, 4))
#     issue_rate      = fields.Float(string='Issue Rate',   readonly=True, digits=(16, 4))
#     balance         = fields.Float(string='Balance',      readonly=True, digits=(16, 4))
#     uom             = fields.Char(string='Unit',          readonly=True)
#     invoice_status  = fields.Char(string='Invoice Status', readonly=True)
#     move_id         = fields.Many2one('stock.move',       string='Stock Move',      readonly=True)
#     company_id      = fields.Many2one('res.company',      string='Company',         readonly=True)
#
#     # ------------------------------------------------------------------
#     def _table_exists(self, table_name):
#         self.env.cr.execute("""
#             SELECT EXISTS (
#                 SELECT 1 FROM information_schema.tables
#                 WHERE table_schema = 'public' AND table_name = %s
#             )
#         """, (table_name,))
#         return self.env.cr.fetchone()[0]
#
#     def _col_exists(self, table_name, col_name):
#         self.env.cr.execute("""
#             SELECT EXISTS (
#                 SELECT 1 FROM information_schema.columns
#                 WHERE table_schema = 'public'
#                   AND table_name   = %s
#                   AND column_name  = %s
#             )
#         """, (table_name, col_name))
#         return self.env.cr.fetchone()[0]
#
#     def init(self):
#         tools.drop_view_if_exists(self.env.cr, self._table)
#
#         # ── Detect optional tables ────────────────────────────────────
#         has_svl  = self._table_exists('stock_valuation_layer')
#         has_so   = self._table_exists('sale_order')
#         has_po   = self._table_exists('purchase_order')
#
#         # ── Detect safe fallback columns ─────────────────────────────
#         # stock_move.reference exists in Odoo 17+
#         sm_ref   = 'sm.reference' if self._col_exists('stock_move', 'reference') else 'sm.origin'
#         # sale_order.invoice_status
#         so_inv   = 'so.invoice_status' if has_so and self._col_exists('sale_order', 'invoice_status') else "NULL::varchar"
#         # purchase_order.invoice_status
#         po_inv   = 'po.invoice_status' if has_po and self._col_exists('purchase_order', 'invoice_status') else "NULL::varchar"
#
#         # ── Cost CTE (stock_valuation_layer when available) ───────────
#         if has_svl:
#             cost_cte = """
# move_cost AS (
#     SELECT
#         stock_move_id,
#         CASE WHEN SUM(ABS(quantity)) > 0
#              THEN SUM(ABS(value)) / SUM(ABS(quantity))
#              ELSE 0
#         END AS unit_cost
#     FROM stock_valuation_layer
#     WHERE stock_move_id IS NOT NULL
#     GROUP BY stock_move_id
# ),"""
#             cost_join  = "LEFT JOIN move_cost mc ON mc.stock_move_id = sm.id"
#             cost_field = "COALESCE(mc.unit_cost, 0)"
#         else:
#             cost_cte   = ""
#             cost_join  = ""
#             cost_field = "0::numeric"
#
#         # ── Sale order fragments ──────────────────────────────────────
#         if has_so:
#             so_join = "LEFT JOIN sale_order so ON so.name = sm.origin"
#             so_name = "so.name"
#             so_cond = "so.id IS NOT NULL"
#         else:
#             so_join = ""
#             so_name = "NULL::varchar"
#             so_cond = "FALSE"
#
#         # ── Purchase order fragments ──────────────────────────────────
#         if has_po:
#             po_join = "LEFT JOIN purchase_order po ON po.name = sm.origin"
#             po_name = "po.name"
#             po_cond = "po.id IS NOT NULL"
#         else:
#             po_join = ""
#             po_name = "NULL::varchar"
#             po_cond = "FALSE"
#
#         sql = f"""
# CREATE OR REPLACE VIEW product_stock_ledger AS
#
# WITH
# -- 1. Map every internal location to its warehouse (distinct to avoid duplicate rows)
# loc_warehouse AS (
#     SELECT DISTINCT ON (sl.id)
#         sl.id AS location_id,
#         sw.id AS warehouse_id
#     FROM stock_location sl
#     JOIN stock_warehouse sw
#         ON sl.id = sw.lot_stock_id
#         OR sl.complete_name LIKE (
#             SELECT complete_name || '/%'
#             FROM stock_location root
#             WHERE root.id = sw.lot_stock_id
#         )
#     WHERE sl.usage = 'internal'
#     ORDER BY sl.id, sw.id
# ),
# {cost_cte}
#
# -- 2. Main ledger
# ledger AS (
#     SELECT
#         sml.id                                               AS id,
#         sml.product_id                                       AS product_id,
#         COALESCE(wh_src.warehouse_id, wh_dest.warehouse_id) AS warehouse_id,
#         sm.date                                              AS date,
#
#         -- Voucher: SO name → PO name → picking name → move origin/reference
#         COALESCE({so_name}, {po_name}, sp.name, sm.origin, {sm_ref})
#                                                              AS voucher,
#
#         -- Particulars: move origin → move reference → picking name
#         COALESCE(sm.origin, {sm_ref}, sp.name)               AS particulars,
#
#         -- Movement type
#         CASE
#             WHEN src_loc.usage = 'supplier'                          THEN 'IN'
#             WHEN dest_loc.usage = 'customer'                         THEN 'OUT'
#             WHEN src_loc.usage = 'customer'                          THEN 'IN'
#             WHEN dest_loc.usage = 'supplier'                         THEN 'OUT'
#             WHEN src_loc.usage  IN ('internal','transit')
#              AND dest_loc.usage IN ('internal','transit')            THEN 'INT'
#             WHEN dest_loc.usage = 'internal'                         THEN 'IN'
#             WHEN src_loc.usage  = 'internal'                         THEN 'OUT'
#             ELSE 'INT'
#         END                                                  AS move_type,
#
#         -- Received qty
#         CASE
#             WHEN dest_loc.usage = 'internal' AND src_loc.usage != 'internal'
#                 THEN sml.quantity
#             WHEN src_loc.usage = 'customer'
#                 THEN sml.quantity
#             ELSE 0
#         END                                                  AS rec_qty,
#
#         -- Received rate
#         CASE
#             WHEN dest_loc.usage = 'internal' AND src_loc.usage != 'internal'
#                 THEN {cost_field}
#             WHEN src_loc.usage = 'customer'
#                 THEN {cost_field}
#             ELSE 0
#         END                                                  AS rec_rate,
#
#         -- Issue qty
#         CASE
#             WHEN src_loc.usage = 'internal' AND dest_loc.usage != 'internal'
#                 THEN sml.quantity
#             ELSE 0
#         END                                                  AS issue_qty,
#
#         -- Issue rate
#         CASE
#             WHEN src_loc.usage = 'internal' AND dest_loc.usage != 'internal'
#                 THEN {cost_field}
#             ELSE 0
#         END                                                  AS issue_rate,
#
#         -- Running balance per product + warehouse
#         SUM(
#             CASE
#                 WHEN dest_loc.usage = 'internal' AND src_loc.usage != 'internal'
#                     THEN  sml.quantity
#                 WHEN src_loc.usage = 'customer'
#                     THEN  sml.quantity
#                 WHEN src_loc.usage = 'internal' AND dest_loc.usage != 'internal'
#                     THEN -sml.quantity
#                 ELSE 0
#             END
#         ) OVER (
#             PARTITION BY sml.product_id,
#                          COALESCE(wh_src.warehouse_id, wh_dest.warehouse_id)
#             ORDER BY sm.date, sml.id
#             ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
#         )                                                    AS balance,
#
#         uom_u.name                                           AS uom,
#
#         -- Invoice status from SO or PO
#         CASE
#             WHEN {so_cond} THEN {so_inv}
#             WHEN {po_cond} THEN {po_inv}
#             ELSE NULL
#         END                                                  AS invoice_status,
#
#         sm.id         AS move_id,
#         sm.company_id AS company_id
#
#     FROM stock_move_line sml
#
#     JOIN stock_move sm
#         ON sm.id    = sml.move_id
#        AND sm.state = 'done'
#
#     JOIN stock_location src_loc  ON src_loc.id  = sml.location_id
#     JOIN stock_location dest_loc ON dest_loc.id = sml.location_dest_id
#
#     LEFT JOIN loc_warehouse wh_src
#         ON wh_src.location_id = sml.location_id
#        AND src_loc.usage = 'internal'
#
#     LEFT JOIN loc_warehouse wh_dest
#         ON wh_dest.location_id = sml.location_dest_id
#        AND dest_loc.usage = 'internal'
#
#     LEFT JOIN uom_uom    uom_u ON uom_u.id = sml.product_uom_id
#     LEFT JOIN stock_picking sp ON sp.id    = sml.picking_id
#
#     {cost_join}
#     {so_join}
#     {po_join}
#
#     WHERE sm.state = 'done'
# )
#
# SELECT * FROM ledger
# ;
#         """
#
#         self.env.cr.execute(sql)
#
#     # ------------------------------------------------------------------
#     def write(self, vals):
#         raise UserError('Stock Ledger records are read-only.')
#
#     def create(self, vals):
#         raise UserError('Stock Ledger records are read-only.')
#
#     def unlink(self):
#         raise UserError('Stock Ledger records are read-only.')
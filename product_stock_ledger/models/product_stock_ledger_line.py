# product_stock_ledger/models/product_stock_ledger_line.py
from odoo import fields, models, api, tools


class ProductStockLedgerLine(models.Model):
    _name = 'product.stock.ledger.line'
    _description = 'Product Stock Ledger (Live View)'
    _auto = False          # Odoo will NOT create a real table — we define the SQL view below
    _order = 'date asc, move_id asc'

    # ── Fields (mapped to SQL columns) ──────────────────────────────────────
    move_id        = fields.Many2one('stock.move',      string='Move',      readonly=True)
    product_id     = fields.Many2one('product.product', string='Product',   readonly=True)
    warehouse_id   = fields.Many2one('stock.warehouse', string='Warehouse', readonly=True)
    date           = fields.Date(string='Date',         readonly=True)
    voucher        = fields.Char(string='Voucher',      readonly=True)
    particulars    = fields.Char(string='Particulars',  readonly=True)
    move_type      = fields.Char(string='Type',         readonly=True)
    rec_qty        = fields.Float(string='Rec. Qty',    readonly=True)
    rec_rate       = fields.Float(string='Rec. Rate',   readonly=True)
    issue_qty      = fields.Float(string='Issue Qty',   readonly=True)
    issue_rate     = fields.Float(string='Issue Rate',  readonly=True)
    balance        = fields.Float(string='Balance',     readonly=True)
    uom            = fields.Char(string='Unit',         readonly=True)
    invoice_status = fields.Char(string='Invoice Status', readonly=True)

    # ── SQL view ─────────────────────────────────────────────────────────────
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (

            WITH

            /* 1. Classify every done stock move */
            classified AS (
                SELECT
                    sm.id                                           AS move_id,
                    sm.product_id,
                    sm.date::date                                   AS date,
                    COALESCE(sm.reference, sm.name, '')             AS voucher,
                    sm.product_uom_qty                              AS qty,

                    /* move direction */
                    CASE
                        WHEN dest.usage = 'internal'
                         AND src.usage  <> 'internal'   THEN 'incoming'
                        WHEN src.usage  = 'internal'
                         AND dest.usage <> 'internal'   THEN 'outgoing'
                        ELSE                                 'internal'
                    END                                             AS move_type,

                    /* warehouse: first match in dest, fallback src */
                    COALESCE(
                        (SELECT sw.id FROM stock_warehouse sw
                          WHERE dest.complete_name LIKE sw.code || '/%%'
                             OR dest.id = sw.lot_stock_id
                          LIMIT 1),
                        (SELECT sw.id FROM stock_warehouse sw
                          WHERE src.complete_name LIKE sw.code || '/%%'
                             OR src.id = sw.lot_stock_id
                          LIMIT 1)
                    )                                               AS warehouse_id,

                    /* particulars */
                    CONCAT(
                        COALESCE(rp.name || ' - ', ''),
                        src.complete_name, ' → ', dest.complete_name
                    )                                               AS particulars,

                    /* unit price */
                    COALESCE(sm.price_unit, pp.standard_price, 0)  AS price_unit,

                    /* uom */
                    uu.name                                         AS uom,

                    /* picking context for invoice status */
                    spt.code                                        AS picking_type_code,
                    sm.purchase_line_id,
                    sm.sale_line_id

                FROM  stock_move          sm
                JOIN  stock_location      src   ON src.id   = sm.location_id
                JOIN  stock_location      dest  ON dest.id  = sm.location_dest_id
                JOIN  product_product     pp    ON pp.id    = sm.product_id
                JOIN  uom_uom             uu    ON uu.id    = sm.product_uom
                LEFT JOIN stock_picking       sp   ON sp.id   = sm.picking_id
                LEFT JOIN stock_picking_type  spt  ON spt.id  = sp.picking_type_id
                LEFT JOIN res_partner         rp   ON rp.id   = sp.partner_id
                WHERE sm.state = 'done'
            ),

            /* 2. Running balance per (product, warehouse) using a window fn */
            with_balance AS (
                SELECT
                    c.*,
                    SUM(
                        CASE move_type
                            WHEN 'incoming' THEN  qty
                            WHEN 'outgoing' THEN -qty
                            ELSE 0
                        END
                    ) OVER (
                        PARTITION BY product_id, warehouse_id
                        ORDER BY date, move_id
                        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                    )                                               AS balance
                FROM classified c
            )

            /* 3. Final output */
            SELECT
                wb.move_id                                          AS id,
                wb.move_id,
                wb.product_id,
                wb.warehouse_id,
                wb.date,
                wb.voucher,
                wb.particulars,

                CASE wb.move_type
                    WHEN 'incoming' THEN 'Receipts'
                    WHEN 'outgoing' THEN 'Delivery'
                    ELSE                 'Internal Transfer'
                END                                                 AS move_type,

                CASE WHEN wb.move_type = 'incoming' THEN wb.qty        ELSE 0 END AS rec_qty,
                CASE WHEN wb.move_type = 'incoming' THEN wb.price_unit ELSE 0 END AS rec_rate,
                CASE WHEN wb.move_type = 'outgoing' THEN wb.qty        ELSE 0 END AS issue_qty,
                CASE WHEN wb.move_type = 'outgoing' THEN wb.price_unit ELSE 0 END AS issue_rate,

                wb.balance,
                wb.uom,

                /* Invoice status from PO / SO */
                CASE
                    WHEN wb.picking_type_code = 'incoming' THEN
                        CASE COALESCE(
                                (SELECT po.invoice_status
                                   FROM purchase_order_line pol
                                   JOIN purchase_order po ON po.id = pol.order_id
                                  WHERE pol.id = wb.purchase_line_id LIMIT 1),
                                'none')
                            WHEN 'invoiced'   THEN 'Invoiced'
                            WHEN 'to invoice' THEN 'To Invoice'
                            ELSE                   'Not Invoiced'
                        END
                    WHEN wb.picking_type_code = 'outgoing' THEN
                        CASE COALESCE(
                                (SELECT so.invoice_status
                                   FROM sale_order_line sol
                                   JOIN sale_order so ON so.id = sol.order_id
                                  WHERE sol.id = wb.sale_line_id LIMIT 1),
                                'none')
                            WHEN 'invoiced'   THEN 'Invoiced'
                            WHEN 'to invoice' THEN 'To Invoice'
                            ELSE                   'Not Invoiced'
                        END
                    WHEN wb.picking_type_code = 'internal' THEN 'Internal'
                    ELSE 'N/A'
                END                                                 AS invoice_status

            FROM with_balance wb
            )
        """ % self._table)

    def action_open_move(self):
        """Open the underlying stock move form (optional drill-down)."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Stock Move',
            'res_model': 'stock.move',
            'res_id': self.move_id.id,
            'view_mode': 'form',
            'target': 'new',
        }
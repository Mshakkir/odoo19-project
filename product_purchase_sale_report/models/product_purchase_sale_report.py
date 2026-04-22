# -*- coding: utf-8 -*-
from odoo import models, fields, tools


class ProductPurchaseSaleReport(models.Model):
    _name = 'product.purchase.sale.report'
    _description = 'Product Purchase & Sale Combined Report'
    _auto = False
    _rec_name = 'product_id'
    _order = 'transaction_date desc'

    product_id          = fields.Many2one('product.product',   string='Product',          readonly=True)
    product_tmpl_id     = fields.Many2one('product.template',  string='Product Template',  readonly=True)
    categ_id            = fields.Many2one('product.category',  string='Product Category',  readonly=True)
    transaction_date    = fields.Date('Date',                                               readonly=True)
    transaction_type    = fields.Selection([('purchase','Purchase'),('sale','Sale')],
                                           string='Type',                                  readonly=True)
    company_id          = fields.Many2one('res.company',       string='Company',           readonly=True)

    vendor_id           = fields.Many2one('res.partner',       string='Vendor',            readonly=True)
    bill_number         = fields.Char('Bill Number',                                        readonly=True)
    bill_id             = fields.Many2one('account.move',      string='Bill',              readonly=True)
    receipt_number      = fields.Char('Receipt Number',                                     readonly=True)
    picking_id          = fields.Many2one('stock.picking',     string='Receipt/Delivery',  readonly=True)
    purchase_order_id   = fields.Many2one('purchase.order',    string='Purchase Order',    readonly=True)
    purchase_order_name = fields.Char('Purchase Order Ref',                                 readonly=True)

    customer_id         = fields.Many2one('res.partner',       string='Customer',          readonly=True)
    invoice_number      = fields.Char('Invoice Number',                                     readonly=True)
    invoice_id          = fields.Many2one('account.move',      string='Invoice',           readonly=True)
    delivery_number     = fields.Char('Delivery Number',                                    readonly=True)
    sale_order_id       = fields.Many2one('sale.order',        string='Sale Order',        readonly=True)
    sale_order_name     = fields.Char('Sale Order Ref',                                     readonly=True)

    qty                 = fields.Float('Quantity',                                          readonly=True)
    unit_price          = fields.Float('Unit Rate',                                         readonly=True)
    price_subtotal      = fields.Float('Subtotal',                                          readonly=True)
    currency_id         = fields.Many2one('res.currency',      string='Currency',          readonly=True)
    uom_id              = fields.Many2one('uom.uom',           string='Unit of Measure',   readonly=True)

    # ── helpers ────────────────────────────────────────────────────────────────
    def _col_exists(self, table, col):
        self.env.cr.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema='public' AND table_name=%s AND column_name=%s
            )
        """, (table, col))
        return self.env.cr.fetchone()[0]

    def _table_exists(self, table):
        self.env.cr.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema='public' AND table_name=%s
            )
        """, (table,))
        return self.env.cr.fetchone()[0]

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)

        # ── CE-safe: stock_picking does NOT have purchase_id / sale_id in CE ──
        # Link receipts via:  po → pol → stock_move.purchase_line_id → sml → sp
        # Link deliveries via: so → sol → stock_move.sale_line_id   → sml → sp
        #
        # Also: account_move_line has no sale_line_ids array in plain SQL.
        # Use sale_order_line_invoice_rel join table instead.

        has_sp_purchase_id = self._col_exists('stock_picking', 'purchase_id')
        has_sp_sale_id     = self._col_exists('stock_picking', 'sale_id')
        has_sol_inv_rel    = self._table_exists('sale_order_line_invoice_rel')
        has_aml_pol        = self._col_exists('account_move_line', 'purchase_line_id')

        # ── Receipt join (purchase side) ──────────────────────────────────────
        # Preferred: sp.purchase_id (if column exists)
        # Fallback:  join via stock_move lines
        if has_sp_purchase_id:
            receipt_join = """
            LEFT JOIN stock_picking sp
                ON sp.purchase_id = po.id
               AND sp.state = 'done'
               AND sp.picking_type_code = 'incoming'"""
        else:
            # CE path: po → pol → stock_move → stock_move_line → stock_picking
            receipt_join = """
            LEFT JOIN stock_picking sp
                ON sp.id = (
                    SELECT sml.picking_id
                    FROM stock_move sm2
                    JOIN stock_move_line sml ON sml.move_id = sm2.id
                    WHERE sm2.purchase_line_id = pol.id
                      AND sm2.state = 'done'
                      AND sml.picking_id IS NOT NULL
                    LIMIT 1
                )"""

        # ── Delivery join (sale side) ─────────────────────────────────────────
        if has_sp_sale_id:
            delivery_join = """
            LEFT JOIN stock_picking sp
                ON sp.sale_id = so.id
               AND sp.state = 'done'
               AND sp.picking_type_code = 'outgoing'"""
        else:
            delivery_join = """
            LEFT JOIN stock_picking sp
                ON sp.id = (
                    SELECT sml.picking_id
                    FROM stock_move sm2
                    JOIN stock_move_line sml ON sml.move_id = sm2.id
                    WHERE sm2.sale_line_id = sol.id
                      AND sm2.state = 'done'
                      AND sml.picking_id IS NOT NULL
                    LIMIT 1
                )"""

        # ── Sale order line join from invoice line ────────────────────────────
        # account_move_line.sale_line_ids is an ORM Many2many — not a real column.
        # The actual relation table is sale_order_line_invoice_rel.
        if has_sol_inv_rel:
            sale_line_join = """
            LEFT JOIN sale_order_line_invoice_rel sol_rel
                ON sol_rel.invoice_line_id = aml.id
            LEFT JOIN sale_order_line sol
                ON sol.id = sol_rel.order_line_id"""
        else:
            # Older builds may store it differently; fall back to NULL
            sale_line_join = """
            LEFT JOIN sale_order_line sol ON FALSE"""

        # ── Purchase line join from invoice line ──────────────────────────────
        if has_aml_pol:
            pur_line_join = """
            LEFT JOIN purchase_order_line pol
                ON pol.id = aml.purchase_line_id"""
        else:
            pur_line_join = """
            LEFT JOIN purchase_order_line pol ON FALSE"""

        sql = """
            CREATE OR REPLACE VIEW %(table)s AS (

            -- ══════════════════════════════════════════════════
            -- PURCHASE LINES (Vendor Bills linked to Receipts)
            -- ══════════════════════════════════════════════════
            SELECT
                ROW_NUMBER() OVER ()        AS id,
                aml.product_id              AS product_id,
                pt.id                       AS product_tmpl_id,
                pt.categ_id                 AS categ_id,
                am.invoice_date             AS transaction_date,
                'purchase'::varchar         AS transaction_type,
                am.company_id               AS company_id,

                am.partner_id               AS vendor_id,
                NULL::integer               AS customer_id,

                am.name                     AS bill_number,
                am.id                       AS bill_id,

                sp.name                     AS receipt_number,
                sp.id                       AS picking_id,

                po.id                       AS purchase_order_id,
                po.name                     AS purchase_order_name,

                NULL::varchar               AS invoice_number,
                NULL::integer               AS invoice_id,
                NULL::varchar               AS delivery_number,
                NULL::integer               AS sale_order_id,
                NULL::varchar               AS sale_order_name,

                aml.quantity                AS qty,
                aml.price_unit              AS unit_price,
                aml.price_subtotal          AS price_subtotal,
                am.currency_id              AS currency_id,
                aml.product_uom_id          AS uom_id

            FROM account_move_line aml
            JOIN account_move am
                ON am.id = aml.move_id
               AND am.move_type = 'in_invoice'
               AND am.state IN ('posted', 'draft')
            JOIN product_product pp
                ON pp.id = aml.product_id
            JOIN product_template pt
                ON pt.id = pp.product_tmpl_id
            %(pur_line_join)s
            LEFT JOIN purchase_order po
                ON po.id = pol.order_id
            %(receipt_join)s
            WHERE aml.product_id IS NOT NULL
              AND aml.display_type NOT IN ('line_section', 'line_note')

            UNION ALL

            -- ══════════════════════════════════════════════════
            -- SALE LINES (Customer Invoices linked to Deliveries)
            -- ══════════════════════════════════════════════════
            SELECT
                ROW_NUMBER() OVER ()        AS id,
                aml.product_id              AS product_id,
                pt.id                       AS product_tmpl_id,
                pt.categ_id                 AS categ_id,
                am.invoice_date             AS transaction_date,
                'sale'::varchar             AS transaction_type,
                am.company_id               AS company_id,

                NULL::integer               AS vendor_id,
                am.partner_id               AS customer_id,

                NULL::varchar               AS bill_number,
                NULL::integer               AS bill_id,
                NULL::varchar               AS receipt_number,
                NULL::integer               AS picking_id,
                NULL::integer               AS purchase_order_id,
                NULL::varchar               AS purchase_order_name,

                am.name                     AS invoice_number,
                am.id                       AS invoice_id,

                sp.name                     AS delivery_number,
                so.id                       AS sale_order_id,
                so.name                     AS sale_order_name,

                aml.quantity                AS qty,
                aml.price_unit              AS unit_price,
                aml.price_subtotal          AS price_subtotal,
                am.currency_id              AS currency_id,
                aml.product_uom_id          AS uom_id

            FROM account_move_line aml
            JOIN account_move am
                ON am.id = aml.move_id
               AND am.move_type = 'out_invoice'
               AND am.state IN ('posted', 'draft')
            JOIN product_product pp
                ON pp.id = aml.product_id
            JOIN product_template pt
                ON pt.id = pp.product_tmpl_id
            %(sale_line_join)s
            LEFT JOIN sale_order so
                ON so.id = sol.order_id
            %(delivery_join)s
            WHERE aml.product_id IS NOT NULL
              AND aml.display_type NOT IN ('line_section', 'line_note')
            )
        """ % {
            'table':          self._table,
            'pur_line_join':  pur_line_join,
            'receipt_join':   receipt_join,
            'sale_line_join': sale_line_join,
            'delivery_join':  delivery_join,
        }

        self.env.cr.execute(sql)
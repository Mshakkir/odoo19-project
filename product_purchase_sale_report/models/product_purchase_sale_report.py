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
    date_str            = fields.Char('Date',                                               readonly=True)
    transaction_type    = fields.Selection([('purchase','Purchase'),('sale','Sale')],
                                           string='Type',                                  readonly=True)
    company_id          = fields.Many2one('res.company',       string='Company',           readonly=True)
    warehouse_id        = fields.Many2one('stock.warehouse',   string='Warehouse',         readonly=True)

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

    def _col_type(self, table, col):
        self.env.cr.execute("""
            SELECT data_type FROM information_schema.columns
            WHERE table_schema='public' AND table_name=%s AND column_name=%s
        """, (table, col))
        row = self.env.cr.fetchone()
        return row[0] if row else None

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)

        has_sol_inv_rel    = self._table_exists('sale_order_line_invoice_rel')
        has_aml_pol        = self._col_exists('account_move_line', 'purchase_line_id')

        # ── Detect jsonb vs varchar for stock_location.complete_name ──────────
        loc_cn_type = self._col_type('stock_location', 'complete_name')
        if loc_cn_type and 'json' in loc_cn_type.lower():
            sl_cn   = "(sl.complete_name->>'en_US')"
            root_cn = "(root.complete_name->>'en_US')"
        else:
            sl_cn   = "sl.complete_name"
            root_cn = "root.complete_name"

        # ── Sale order line join from invoice line ────────────────────────────
        if has_sol_inv_rel:
            sale_line_join = """
            LEFT JOIN sale_order_line_invoice_rel sol_rel
                ON sol_rel.invoice_line_id = aml.id
            LEFT JOIN sale_order_line sol
                ON sol.id = sol_rel.order_line_id"""
        else:
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

            -- ══════════════════════════════════════════════════════
            -- CTE: map every internal stock location to a warehouse
            -- (same technique as product.stock.ledger)
            -- ══════════════════════════════════════════════════════
            WITH loc_warehouse AS (
                SELECT DISTINCT ON (sl.id)
                    sl.id  AS location_id,
                    sw.id  AS warehouse_id
                FROM stock_location sl
                JOIN stock_warehouse sw
                    ON sl.id = sw.lot_stock_id
                    OR %(sl_cn)s LIKE (
                        SELECT %(root_cn)s || '/%%'
                        FROM stock_location root
                        WHERE root.id = sw.lot_stock_id
                    )
                WHERE sl.usage = 'internal'
                ORDER BY sl.id, sw.id
            )

            -- ══════════════════════════════════════════════════════
            -- PURCHASE LINES  (Vendor Bills)
            -- Receipt = stock.picking linked via stock_move.picking_id
            -- ══════════════════════════════════════════════════════
            SELECT
                ROW_NUMBER() OVER ()                        AS id,
                aml.product_id                              AS product_id,
                pt.id                                       AS product_tmpl_id,
                pt.categ_id                                 AS categ_id,
                am.invoice_date                             AS transaction_date,
                TO_CHAR(am.invoice_date, 'DD/MM/YY')        AS date_str,
                'purchase'::varchar                         AS transaction_type,
                am.company_id                               AS company_id,

                lw.warehouse_id                             AS warehouse_id,

                am.partner_id                               AS vendor_id,
                NULL::integer                               AS customer_id,

                am.name                                     AS bill_number,
                am.id                                       AS bill_id,

                sp.name                                     AS receipt_number,
                sp.id                                       AS picking_id,

                po.id                                       AS purchase_order_id,
                po.name                                     AS purchase_order_name,

                NULL::varchar                               AS invoice_number,
                NULL::integer                               AS invoice_id,
                NULL::varchar                               AS delivery_number,
                NULL::integer                               AS sale_order_id,
                NULL::varchar                               AS sale_order_name,

                aml.quantity                                AS qty,
                aml.price_unit                              AS unit_price,
                aml.price_subtotal                          AS price_subtotal,
                am.currency_id                              AS currency_id,
                aml.product_uom_id                          AS uom_id

            FROM account_move_line aml
            JOIN account_move am
                ON am.id        = aml.move_id
               AND am.move_type = 'in_invoice'
               AND am.state     IN ('posted', 'draft')
            JOIN product_product pp
                ON pp.id = aml.product_id
            JOIN product_template pt
                ON pt.id = pp.product_tmpl_id
            %(pur_line_join)s
            LEFT JOIN purchase_order po
                ON po.id = pol.order_id
            -- Get the receipt picking directly from stock_move.picking_id
            LEFT JOIN stock_move sm_pur
                ON sm_pur.purchase_line_id = pol.id
               AND sm_pur.state = 'done'
            LEFT JOIN stock_picking sp
                ON sp.id = sm_pur.picking_id
               AND EXISTS (
                   SELECT 1 FROM stock_picking_type spt
                   WHERE spt.id = sp.picking_type_id
                     AND spt.code = 'incoming'
               )
            -- Warehouse via the picking's source/dest location
            LEFT JOIN loc_warehouse lw
                ON lw.location_id = sp.location_dest_id
            WHERE aml.product_id IS NOT NULL
              AND aml.display_type NOT IN ('line_section', 'line_note')

            UNION ALL

            -- ══════════════════════════════════════════════════════
            -- SALE LINES  (Customer Invoices)
            -- Delivery = stock.picking linked via stock_move.picking_id
            -- ══════════════════════════════════════════════════════
            SELECT
                ROW_NUMBER() OVER ()                        AS id,
                aml.product_id                              AS product_id,
                pt.id                                       AS product_tmpl_id,
                pt.categ_id                                 AS categ_id,
                am.invoice_date                             AS transaction_date,
                TO_CHAR(am.invoice_date, 'DD/MM/YY')        AS date_str,
                'sale'::varchar                             AS transaction_type,
                am.company_id                               AS company_id,

                lw.warehouse_id                             AS warehouse_id,

                NULL::integer                               AS vendor_id,
                am.partner_id                               AS customer_id,

                NULL::varchar                               AS bill_number,
                NULL::integer                               AS bill_id,
                NULL::varchar                               AS receipt_number,
                NULL::integer                               AS picking_id,
                NULL::integer                               AS purchase_order_id,
                NULL::varchar                               AS purchase_order_name,

                am.name                                     AS invoice_number,
                am.id                                       AS invoice_id,

                sp.name                                     AS delivery_number,
                so.id                                       AS sale_order_id,
                so.name                                     AS sale_order_name,

                aml.quantity                                AS qty,
                aml.price_unit                              AS unit_price,
                aml.price_subtotal                          AS price_subtotal,
                am.currency_id                              AS currency_id,
                aml.product_uom_id                          AS uom_id

            FROM account_move_line aml
            JOIN account_move am
                ON am.id        = aml.move_id
               AND am.move_type = 'out_invoice'
               AND am.state     IN ('posted', 'draft')
            JOIN product_product pp
                ON pp.id = aml.product_id
            JOIN product_template pt
                ON pt.id = pp.product_tmpl_id
            %(sale_line_join)s
            LEFT JOIN sale_order so
                ON so.id = sol.order_id
            -- Get the delivery picking directly from stock_move.picking_id
            LEFT JOIN stock_move sm_sal
                ON sm_sal.sale_line_id = sol.id
               AND sm_sal.state = 'done'
            LEFT JOIN stock_picking sp
                ON sp.id = sm_sal.picking_id
               AND EXISTS (
                   SELECT 1 FROM stock_picking_type spt
                   WHERE spt.id = sp.picking_type_id
                     AND spt.code = 'outgoing'
               )
            -- Warehouse via the picking's source location
            LEFT JOIN loc_warehouse lw
                ON lw.location_id = sp.location_id
            WHERE aml.product_id IS NOT NULL
              AND aml.display_type NOT IN ('line_section', 'line_note')
            )
        """ % {
            'table':          self._table,
            'sl_cn':          sl_cn,
            'root_cn':        root_cn,
            'pur_line_join':  pur_line_join,
            'sale_line_join': sale_line_join,
        }

        self.env.cr.execute(sql)
# -*- coding: utf-8 -*-
from odoo import models, fields, tools


class ProductPurchaseSaleReport(models.Model):
    _name = 'product.purchase.sale.report'
    _description = 'Product Purchase & Sale Combined Report'
    _auto = False
    _rec_name = 'product_id'
    _order = 'transaction_date desc'

    # ── Common Fields ──────────────────────────────────────────
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    product_tmpl_id = fields.Many2one('product.template', string='Product Template', readonly=True)
    categ_id = fields.Many2one('product.category', string='Product Category', readonly=True)
    transaction_date = fields.Date(string='Date', readonly=True)
    transaction_type = fields.Selection([
        ('purchase', 'Purchase'),
        ('sale', 'Sale'),
    ], string='Type', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)

    # ── Purchase Fields ─────────────────────────────────────────
    vendor_id = fields.Many2one('res.partner', string='Vendor', readonly=True)
    bill_number = fields.Char(string='Bill Number', readonly=True)
    bill_id = fields.Many2one('account.move', string='Bill', readonly=True)
    receipt_number = fields.Char(string='Receipt Number', readonly=True)
    picking_id = fields.Many2one('stock.picking', string='Receipt/Delivery', readonly=True)
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order', readonly=True)
    purchase_order_name = fields.Char(string='Purchase Order Ref', readonly=True)

    # ── Sale Fields ─────────────────────────────────────────────
    customer_id = fields.Many2one('res.partner', string='Customer', readonly=True)
    invoice_number = fields.Char(string='Invoice Number', readonly=True)
    invoice_id = fields.Many2one('account.move', string='Invoice', readonly=True)
    delivery_number = fields.Char(string='Delivery Number', readonly=True)
    sale_order_id = fields.Many2one('sale.order', string='Sale Order', readonly=True)
    sale_order_name = fields.Char(string='Sale Order Ref', readonly=True)

    # ── Quantity & Price ────────────────────────────────────────
    qty = fields.Float(string='Quantity', readonly=True)
    unit_price = fields.Float(string='Unit Rate', readonly=True)
    price_subtotal = fields.Float(string='Subtotal', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (

            -- ══════════════════════════════════════════════════
            -- PURCHASE LINES (Vendor Bills linked to Receipts)
            -- ══════════════════════════════════════════════════
            SELECT
                ROW_NUMBER() OVER ()                        AS id,
                aml.product_id                              AS product_id,
                pt.id                                       AS product_tmpl_id,
                pt.categ_id                                 AS categ_id,
                am.invoice_date                             AS transaction_date,
                'purchase'                                  AS transaction_type,
                am.company_id                               AS company_id,

                -- Vendor
                am.partner_id                               AS vendor_id,
                NULL::integer                               AS customer_id,

                -- Bill info
                am.name                                     AS bill_number,
                am.id                                       AS bill_id,

                -- Receipt (Stock Picking linked via Purchase Order)
                sp.name                                     AS receipt_number,
                sp.id                                       AS picking_id,

                -- Purchase Order
                po.id                                       AS purchase_order_id,
                po.name                                     AS purchase_order_name,

                -- Sale (empty for purchase rows)
                NULL::varchar                               AS invoice_number,
                NULL::integer                               AS invoice_id,
                NULL::varchar                               AS delivery_number,
                NULL::integer                               AS sale_order_id,
                NULL::varchar                               AS sale_order_name,

                -- Qty & Price
                aml.quantity                                AS qty,
                aml.price_unit                              AS unit_price,
                aml.price_subtotal                          AS price_subtotal,
                am.currency_id                              AS currency_id,
                aml.product_uom_id                          AS uom_id

            FROM account_move_line aml
            JOIN account_move am
                ON am.id = aml.move_id
                AND am.move_type = 'in_invoice'
                AND am.state IN ('posted', 'draft')
            JOIN product_product pp
                ON pp.id = aml.product_id
            JOIN product_template pt
                ON pt.id = pp.product_tmpl_id
            -- Link bill -> purchase order line -> purchase order
            LEFT JOIN purchase_order_line pol
                ON pol.id = aml.purchase_line_id
            LEFT JOIN purchase_order po
                ON po.id = pol.order_id
            -- Link purchase order -> stock picking (receipts)
            LEFT JOIN stock_picking sp
                ON sp.purchase_id = po.id
                AND sp.state = 'done'
                AND sp.picking_type_code = 'incoming'
            WHERE aml.product_id IS NOT NULL
              AND aml.display_type NOT IN ('line_section', 'line_note')

            UNION ALL

            -- ══════════════════════════════════════════════════
            -- SALE LINES (Customer Invoices linked to Deliveries)
            -- ══════════════════════════════════════════════════
            SELECT
                ROW_NUMBER() OVER ()                        AS id,
                aml.product_id                              AS product_id,
                pt.id                                       AS product_tmpl_id,
                pt.categ_id                                 AS categ_id,
                am.invoice_date                             AS transaction_date,
                'sale'                                      AS transaction_type,
                am.company_id                               AS company_id,

                -- Vendor (empty for sale rows)
                NULL::integer                               AS vendor_id,

                -- Customer
                am.partner_id                               AS customer_id,

                -- Bill/Receipt (empty for sale rows)
                NULL::varchar                               AS bill_number,
                NULL::integer                               AS bill_id,
                NULL::varchar                               AS receipt_number,
                NULL::integer                               AS picking_id,
                NULL::integer                               AS purchase_order_id,
                NULL::varchar                               AS purchase_order_name,

                -- Invoice info
                am.name                                     AS invoice_number,
                am.id                                       AS invoice_id,

                -- Delivery (Stock Picking linked via Sale Order)
                sp.name                                     AS delivery_number,
                sp.id                                       AS sale_order_id,
                so.name                                     AS sale_order_name,

                -- Qty & Price
                aml.quantity                                AS qty,
                aml.price_unit                              AS unit_price,
                aml.price_subtotal                          AS price_subtotal,
                am.currency_id                              AS currency_id,
                aml.product_uom_id                          AS uom_id

            FROM account_move_line aml
            JOIN account_move am
                ON am.id = aml.move_id
                AND am.move_type = 'out_invoice'
                AND am.state IN ('posted', 'draft')
            JOIN product_product pp
                ON pp.id = aml.product_id
            JOIN product_template pt
                ON pt.id = pp.product_tmpl_id
            -- Link invoice -> sale order line -> sale order
            LEFT JOIN sale_order_line sol
                ON sol.id = aml.sale_line_ids[1]
            LEFT JOIN sale_order so
                ON so.id = sol.order_id
            -- Link sale order -> stock picking (deliveries)
            LEFT JOIN stock_picking sp
                ON sp.sale_id = so.id
                AND sp.state = 'done'
                AND sp.picking_type_code = 'outgoing'
            WHERE aml.product_id IS NOT NULL
              AND aml.display_type NOT IN ('line_section', 'line_note')
            )
        """ % self._table)

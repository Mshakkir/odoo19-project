from odoo import models, fields, tools, api
from odoo.exceptions import UserError


class PurchaseReport(models.Model):
    _name = 'purchase.report.view'
    _description = 'Purchase Invoice Report'
    _auto = False
    _order = 'invoice_date desc'

    # Invoice Fields
    invoice_id = fields.Many2one('account.move', string='Invoice', readonly=True)
    invoice_name = fields.Char('Invoice Number', readonly=True)
    invoice_date = fields.Date('Date', readonly=True)

    # Partner/Vendor Fields
    partner_id = fields.Many2one('res.partner', string='Vendor', readonly=True)
    partner_name = fields.Char('Vendor Name', readonly=True)

    # Product Fields
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    product_name = fields.Char('Product', readonly=True)
    product_code = fields.Char('Product Code', readonly=True)
    categ_id = fields.Many2one('product.category', string='Category', readonly=True)
    category_name = fields.Char('Category', readonly=True)

    # Analytic Fields
    analytic_account_ids = fields.Char('Analytic Account', readonly=True)

    # Quantities and Amounts
    quantity = fields.Float('Qty', readonly=True)
    product_uom = fields.Many2one('uom.uom', string='Unit', readonly=True)
    uom_name = fields.Char('Unit', readonly=True)
    price_unit = fields.Float('Rate', readonly=True)
    price_subtotal = fields.Float('Untaxed', readonly=True)
    price_total = fields.Float('Net Total', readonly=True)

    # Company
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT 
                    aml.id as id,
                    am.id as invoice_id,
                    am.name as invoice_name,
                    am.invoice_date as invoice_date,
                    am.partner_id as partner_id,
                    rp.name as partner_name,
                    aml.product_id as product_id,
                    pp.default_code as product_code,
                    pt.name as product_name,
                    pt.categ_id as categ_id,
                    pc.complete_name as category_name,
                    (SELECT string_agg(aa.name, ', ')
                     FROM jsonb_each_text(COALESCE(aml.analytic_distribution, '{}'::jsonb)) AS dist(account_id, percentage)
                     LEFT JOIN account_analytic_account aa ON aa.id = dist.account_id::integer
                     WHERE aa.name IS NOT NULL
                    ) as analytic_account_ids,
                    aml.quantity as quantity,
                    aml.product_uom_id as product_uom,
                    pu.name as uom_name,
                    aml.price_unit as price_unit,
                    aml.price_subtotal as price_subtotal,
                    aml.price_total as price_total,
                    am.company_id as company_id,
                    am.currency_id as currency_id
                FROM 
                    account_move_line aml
                    INNER JOIN account_move am ON aml.move_id = am.id
                    LEFT JOIN res_partner rp ON am.partner_id = rp.id
                    LEFT JOIN product_product pp ON aml.product_id = pp.id
                    LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id
                    LEFT JOIN product_category pc ON pt.categ_id = pc.id
                    LEFT JOIN uom_uom pu ON aml.product_uom_id = pu.id
                WHERE 
                    am.move_type = 'in_invoice'
                    AND am.state = 'posted'
                    AND aml.product_id IS NOT NULL
                    AND aml.display_type = 'product'
            )
        """ % self._table)

from odoo import models, fields, api, tools


class CustomerInvoiceReport(models.Model):
    _name = 'customer.invoice.report'
    _description = 'Customer Invoice Report'
    _auto = False
    _rec_name = 'partner_id'
    _order = 'invoice_date desc'

    # Invoice Information
    invoice_id = fields.Many2one('account.move', string='Invoice', readonly=True)
    invoice_date = fields.Date(string='Invoice Date', readonly=True)
    invoice_number = fields.Char(string='Invoice Number', readonly=True)
    invoice_state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True)
    move_type = fields.Selection([
        ('out_invoice', 'Invoice'),
        ('out_refund', 'Credit Note'),
    ], string='Type', readonly=True)

    # Product Information
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    product_template_id = fields.Many2one('product.template', string='Product Template', readonly=True)
    categ_id = fields.Many2one('product.category', string='Product Category', readonly=True)

    # Customer Information
    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True)
    country_id = fields.Many2one('res.country', string='Country', readonly=True)

    # Salesperson Information
    user_id = fields.Many2one('res.users', string='Salesperson', readonly=True)
    team_id = fields.Many2one('crm.team', string='Sales Team', readonly=True)

    # NEW FIELDS - Analytic Account, Warehouse, and Account
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', readonly=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', readonly=True)
    account_id = fields.Many2one('account.account', string='Account', readonly=True)

    # Quantity and Amount
    quantity = fields.Float(string='Quantity', readonly=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', readonly=True)
    price_unit = fields.Float(string='Unit Price', readonly=True)
    price_subtotal = fields.Monetary(string='Untaxed Total', readonly=True)
    price_total = fields.Monetary(string='Total', readonly=True)
    discount = fields.Float(string='Discount %', readonly=True)

    # Currency
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)

    def init(self):
        """Create SQL view for customer invoice report"""
        tools.drop_view_if_exists(self.env.cr, self._table)
        query = """
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    ail.id as id,
                    am.id as invoice_id,
                    am.invoice_date as invoice_date,
                    am.name as invoice_number,
                    am.state as invoice_state,
                    am.move_type as move_type,
                    ail.product_id as product_id,
                    pt.id as product_template_id,
                    pt.categ_id as categ_id,
                    am.partner_id as partner_id,
                    rp.country_id as country_id,
                    am.invoice_user_id as user_id,
                    am.team_id as team_id,
                    (SELECT aaa.id 
                     FROM account_analytic_account aaa,
                          jsonb_each_text(COALESCE(ail.analytic_distribution, '{}'::jsonb)) as dist
                     WHERE aaa.id = dist.key::integer
                     LIMIT 1
                    ) as analytic_account_id,
                    ail.warehouse_id as warehouse_id,
                    ail.account_id as account_id,
                    CASE 
                        WHEN am.move_type = 'out_refund' THEN -ail.quantity
                        ELSE ail.quantity
                    END as quantity,
                    ail.product_uom_id as uom_id,
                    ail.price_unit as price_unit,
                    CASE 
                        WHEN am.move_type = 'out_refund' THEN -ail.price_subtotal
                        ELSE ail.price_subtotal
                    END as price_subtotal,
                    CASE 
                        WHEN am.move_type = 'out_refund' THEN -ail.price_total
                        ELSE ail.price_total
                    END as price_total,
                    ail.discount as discount,
                    am.currency_id as currency_id,
                    am.company_id as company_id
                FROM
                    account_move_line ail
                    JOIN account_move am ON ail.move_id = am.id
                    LEFT JOIN res_partner rp ON am.partner_id = rp.id
                    LEFT JOIN product_product pp ON ail.product_id = pp.id
                    LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id
                WHERE
                    am.move_type IN ('out_invoice', 'out_refund')
                    AND (ail.display_type IS NULL OR ail.display_type = 'product')
            )
        """ % self._table
        self.env.cr.execute(query)
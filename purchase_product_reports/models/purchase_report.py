from odoo import models, fields, tools


class PurchaseReport(models.Model):
    _name = 'purchase.report.view'
    _description = 'Purchase Invoice Report'
    _auto = False

    invoice_date = fields.Date('Date', readonly=True)
    invoice_name = fields.Char('Invoice', readonly=True)
    partner_name = fields.Char('Vendor', readonly=True)
    product_name = fields.Char('Product', readonly=True)
    quantity = fields.Float('Qty', readonly=True)
    price_total = fields.Float('Total', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT 
                    aml.id as id,
                    am.invoice_date as invoice_date,
                    am.name as invoice_name,
                    rp.name as partner_name,
                    pt.name as product_name,
                    aml.quantity as quantity,
                    aml.price_total as price_total
                FROM account_move_line aml
                JOIN account_move am ON aml.move_id = am.id
                LEFT JOIN res_partner rp ON am.partner_id = rp.id
                LEFT JOIN product_product pp ON aml.product_id = pp.id
                LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id
                WHERE am.move_type = 'in_invoice'
                  AND am.state = 'posted'
                  AND aml.product_id IS NOT NULL
                  AND aml.display_type = 'product'
            )
        """ % self._table)
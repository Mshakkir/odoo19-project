from odoo import models, fields, tools


class PurchaseReport(models.Model):
    _name = 'purchase.report.view'
    _description = 'Purchase Report'
    _auto = False

    order_name = fields.Char('Order', readonly=True)
    order_date = fields.Datetime('Date', readonly=True)
    partner_name = fields.Char('Vendor', readonly=True)
    product_name = fields.Char('Product', readonly=True)
    product_qty = fields.Float('Quantity', readonly=True)
    price_total = fields.Float('Total', readonly=True)
    state = fields.Char('Status', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT 
                    pol.id as id,
                    po.name as order_name,
                    po.date_order as order_date,
                    rp.name as partner_name,
                    pt.name as product_name,
                    pol.product_qty as product_qty,
                    pol.price_total as price_total,
                    po.state as state
                FROM purchase_order_line pol
                JOIN purchase_order po ON pol.order_id = po.id
                LEFT JOIN res_partner rp ON po.partner_id = rp.id
                LEFT JOIN product_product pp ON pol.product_id = pp.id
                LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id
            )
        """ % self._table)
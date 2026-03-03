from odoo import models, fields

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    sale_customer_reference = fields.Char(
        string="Customer Reference",
        compute="_compute_sale_customer_reference",
        store=True
    )

    def _compute_sale_customer_reference(self):
        for picking in self:
            sale = self.env['sale.order'].search(
                [('name', '=', picking.origin)],
                limit=1
            )
            picking.sale_customer_reference = sale.client_order_ref if sale else False
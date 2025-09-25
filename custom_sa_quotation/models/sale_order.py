from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    discount_amount = fields.Monetary(string="Discount", default=0.0)
    freight_amount = fields.Monetary(string="Freight", default=0.0)

    @api.depends('order_line.price_total', 'discount_amount', 'freight_amount', 'order_line.tax_id')
    def _amount_all(self):
        # Call super to preserve original computation
        super(SaleOrder, self)._amount_all()
        for order in self:
            # Override amount_total to include discount and freight
            order.amount_total = order.amount_untaxed - order.discount_amount + order.freight_amount + order.amount_tax

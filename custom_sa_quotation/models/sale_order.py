from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    discount_amount = fields.Monetary(string="Discount", default=0.0)
    freight_amount = fields.Monetary(string="Freight", default=0.0)

    # Extend total computation
    @api.depends('order_line.price_total', 'discount_amount', 'freight_amount')
    def _compute_amount(self):
        for order in self:
            untaxed = sum(line.price_total for line in order.order_line)
            order.amount_untaxed = untaxed
            order.amount_total = untaxed - order.discount_amount + order.freight_amount

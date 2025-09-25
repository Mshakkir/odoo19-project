from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    discount_amount = fields.Monetary(
        string="Discount",
        default=0.0,
        currency_field='currency_id',
        help="Total discount amount applied to this order"
    )
    freight_amount = fields.Monetary(
        string="Freight",
        default=0.0,
        currency_field='currency_id',
        help="Total freight amount applied to this order"
    )

    @api.depends('order_line.price_subtotal', 'order_line.price_tax', 'discount_amount', 'freight_amount')
    def _amount_all(self):
        for order in self:
            amount_untaxed = sum(line.price_subtotal for line in order.order_line)
            amount_tax = sum(line.price_tax for line in order.order_line)

            # Include discount and freight in the calculation
            amount_total = amount_untaxed - order.discount_amount + order.freight_amount + amount_tax

            order.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_total': amount_total,
            })

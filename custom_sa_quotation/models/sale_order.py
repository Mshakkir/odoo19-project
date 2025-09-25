from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    discount_amount = fields.Monetary(string="Discount", default=0.0, currency_field='currency_id')
    freight_amount = fields.Monetary(string="Freight", default=0.0, currency_field='currency_id')

    @api.depends('order_line.price_subtotal', 'order_line.price_tax', 'discount_amount', 'freight_amount')
    def _amount_all(self):
        """
        Compute the amounts of the SO: amount_untaxed, amount_tax, amount_total.
        """
        for order in self:
            amount_untaxed = sum(line.price_subtotal for line in order.order_line)
            amount_tax = sum(line.price_tax for line in order.order_line)

            # apply discount and freight
            amount_total = amount_untaxed + amount_tax - order.discount_amount + order.freight_amount

            order.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_total': amount_total,
            })

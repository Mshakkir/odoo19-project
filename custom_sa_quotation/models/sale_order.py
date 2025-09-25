from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    discount_amount = fields.Monetary(string="Discount", default=0.0)
    freight_amount = fields.Monetary(string="Freight", default=0.0)

    @api.depends('order_line.price_total', 'order_line.tax_id', 'discount_amount', 'freight_amount')
    def _amount_all(self):
        """
        Compute the amounts of the SO: amount_untaxed, amount_tax, amount_total.
        """
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax

            # apply discount and freight
            amount_total = amount_untaxed + amount_tax - order.discount_amount + order.freight_amount

            order.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_total': amount_total,
            })

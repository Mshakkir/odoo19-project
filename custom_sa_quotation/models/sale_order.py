from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    discount_amount = fields.Monetary(string="Discount", default=0.0)
    freight_amount = fields.Monetary(string="Freight", default=0.0)

    @api.depends('order_line.price_total', 'discount_amount', 'freight_amount', 'order_line.tax_id')
    def _amount_all(self):
        for order in self:
            untaxed_amount = sum(line.price_subtotal for line in order.order_line)
            tax_amount = sum(line.price_tax for line in order.order_line)
            order.update({
                'amount_untaxed': untaxed_amount,
                'amount_tax': tax_amount,
                'amount_total': untaxed_amount - order.discount_amount + order.freight_amount + tax_amount,
            })

    @api.onchange('discount_amount', 'freight_amount')
    def _onchange_discount_freight(self):
        self._amount_all()

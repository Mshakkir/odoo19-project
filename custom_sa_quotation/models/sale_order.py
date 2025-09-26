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
        """
        Compute the total amounts of the SO.
        """
        for order in self:
            # Calculate base amounts from order lines
            amount_untaxed = amount_tax = 0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax

            # Apply discount and freight to the total
            amount_total = amount_untaxed + amount_tax - order.discount_amount + order.freight_amount

            # Update the order fields
            order.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_total': amount_total,
            })

    @api.onchange('discount_amount', 'freight_amount', 'order_line')
    def _onchange_discount_freight(self):
        """
        Trigger recalculation when discount, freight, or order lines change
        """
        self._amount_all()
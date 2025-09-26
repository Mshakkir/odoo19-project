from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    discount_amount = fields.Monetary(
        string="Discount",
        default=0.0,
        currency_field='currency_id',
        help="Total discount amount applied to this order",
        readonly=False,
        store=True
    )
    freight_amount = fields.Monetary(
        string="Freight",
        default=0.0,
        currency_field='currency_id',
        help="Total freight amount applied to this order",
        readonly=False,
        store=True
    )

    @api.depends('order_line.price_subtotal', 'order_line.price_tax', 'discount_amount', 'freight_amount')
    def _compute_tax_totals(self):
        """
        Override the tax totals computation to include discount and freight
        """
        super()._compute_tax_totals()
        for order in self:
            if order.tax_totals:
                # Get the current totals
                amount_untaxed = order.tax_totals.get('amount_untaxed', 0.0)
                amount_tax = order.tax_totals.get('amount_tax', 0.0)

                # Calculate new total with discount and freight
                amount_total = amount_untaxed + amount_tax - order.discount_amount + order.freight_amount

                # Update the tax_totals dictionary
                order.tax_totals.update({
                    'amount_total': amount_total,
                    'formatted_amount_total': order.currency_id.format(amount_total) if order.currency_id else str(
                        amount_total),
                })

    @api.depends('order_line.price_subtotal', 'order_line.price_tax', 'discount_amount', 'freight_amount')
    def _amount_all(self):
        """
        Compute the total amounts of the SO including discount and freight.
        """
        for order in self:
            # Calculate base amounts from order lines
            amount_untaxed = sum(line.price_subtotal for line in order.order_line)
            amount_tax = sum(line.price_tax for line in order.order_line)

            # Apply discount and freight to the total
            amount_total = amount_untaxed + amount_tax - order.discount_amount + order.freight_amount

            # Update the order fields
            order.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_total': amount_total,
            })

    @api.onchange('discount_amount', 'freight_amount')
    def _onchange_discount_freight(self):
        """
        Trigger recalculation when discount or freight changes
        """
        for order in self:
            # Trigger recomputation of amounts
            order._amount_all()
            # Also trigger tax totals recomputation if it exists
            if hasattr(order, '_compute_tax_totals'):
                order._compute_tax_totals()
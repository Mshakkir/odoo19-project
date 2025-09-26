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

    @api.depends('order_line.price_subtotal', 'order_line.price_tax', 'discount_amount', 'freight_amount')
    def _compute_tax_totals(self):
        """
        Override to include discount and freight in tax calculations
        """
        super()._compute_tax_totals()
        for order in self:
            if order.tax_totals:
                # Get base amounts
                base_amount_untaxed = sum(line.price_subtotal for line in order.order_line)

                # Calculate new tax amount based on adjusted untaxed amount
                tax_rate = 0.0
                if base_amount_untaxed > 0:
                    original_tax = sum(line.price_tax for line in order.order_line)
                    tax_rate = original_tax / base_amount_untaxed if base_amount_untaxed else 0.0

                # Apply discount/freight to taxable amount
                adjusted_taxable = base_amount_untaxed - order.discount_amount + order.freight_amount
                new_tax_amount = adjusted_taxable * tax_rate

                # Update tax_totals
                order.tax_totals.update({
                    'amount_untaxed': base_amount_untaxed,
                    'amount_tax': new_tax_amount,
                    'amount_total': adjusted_taxable + new_tax_amount,
                    'formatted_amount_untaxed': order.currency_id.format(base_amount_untaxed),
                    'formatted_amount_tax': order.currency_id.format(new_tax_amount),
                    'formatted_amount_total': order.currency_id.format(adjusted_taxable + new_tax_amount),
                })

    @api.onchange('discount_amount', 'freight_amount')
    def _onchange_discount_freight(self):
        """
        Trigger recalculation when discount or freight changes
        """
        for order in self:
            order._amount_all()
            order._compute_tax_totals()
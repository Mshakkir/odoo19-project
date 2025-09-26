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

    po_number = fields.Char(
        string="PO Number",
        help="Customer's Purchase Order Number for reference"
    )

    # Custom computed fields for the new totals section
    custom_untaxed_amount = fields.Monetary(
        string="Untaxed Amount",
        compute="_compute_custom_totals",
        currency_field='currency_id',
        store=False
    )
    custom_gross_total = fields.Monetary(
        string="Gross Total",
        compute="_compute_custom_totals",
        currency_field='currency_id',
        store=False
    )
    custom_tax_amount = fields.Monetary(
        string="VAT Taxes",
        compute="_compute_custom_totals",
        currency_field='currency_id',
        store=False
    )
    custom_net_total = fields.Monetary(
        string="Net Total",
        compute="_compute_custom_totals",
        currency_field='currency_id',
        store=False
    )

    @api.depends('order_line.price_subtotal', 'order_line.price_tax', 'discount_amount', 'freight_amount')
    def _compute_custom_totals(self):
        """
        Compute custom totals including discount and freight
        """
        for order in self:
            # Base amounts from order lines
            untaxed_amount = sum(line.price_subtotal for line in order.order_line if not line.display_type)
            original_tax = sum(line.price_tax for line in order.order_line if not line.display_type)

            # Calculate gross total (after discount and freight, before tax)
            gross_total = untaxed_amount - order.discount_amount + order.freight_amount

            # Calculate tax rate and apply to gross total
            tax_rate = original_tax / untaxed_amount if untaxed_amount > 0 else 0.0
            custom_tax = gross_total * tax_rate

            # Net total (final amount)
            net_total = gross_total + custom_tax

            order.update({
                'custom_untaxed_amount': untaxed_amount,
                'custom_gross_total': gross_total,
                'custom_tax_amount': custom_tax,
                'custom_net_total': net_total,
            })

    @api.onchange('discount_amount', 'freight_amount')
    def _onchange_discount_freight(self):
        """
        Trigger recalculation when discount or freight changes
        """
        self._compute_custom_totals()
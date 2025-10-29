# Copyright 2017 ForgeFlow S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

from odoo import api, fields, models
from odoo.tools.float_utils import float_is_zero


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    discount_fixed = fields.Monetary(
        string="Discount (Fixed)",
        default=0.0,
        currency_field="currency_id",
        help=(
            "Apply a fixed total discount to this line. "
            "This is a total discount amount, not per unit."
        ),
    )

    @api.depends("product_uom_qty", "discount", "price_unit", "discount_fixed")
    def _compute_amount(self):
        """Override to calculate amounts with fixed discount."""
        for line in self:
            if float_is_zero(
                    line.discount_fixed, precision_rounding=line.currency_id.rounding
            ):
                continue

            # Calculate price with fixed discount
            subtotal_before_discount = line.product_uom_qty * line.price_unit

            if line.product_uom_qty and not float_is_zero(
                    line.product_uom_qty, precision_rounding=line.currency_id.rounding
            ):
                # Apply fixed discount to total
                subtotal_after_discount = subtotal_before_discount - line.discount_fixed
                effective_price_unit = subtotal_after_discount / line.product_uom_qty
            else:
                effective_price_unit = line.price_unit

            # Calculate tax
            tax_results = line.tax_id.compute_all(
                effective_price_unit,
                line.currency_id,
                line.product_uom_qty,
                product=line.product_id,
                partner=line.order_id.partner_shipping_id,
            )

            line.update({
                'price_tax': tax_results['total_included'] - tax_results['total_excluded'],
                'price_total': tax_results['total_included'],
                'price_subtotal': tax_results['total_excluded'],
            })

        # Process lines without fixed discount normally
        super(SaleOrderLine, self.filtered(
            lambda l: float_is_zero(l.discount_fixed, precision_rounding=l.currency_id.rounding)
        ))._compute_amount()

    @api.onchange("discount_fixed", "price_unit", "product_uom_qty")
    def _onchange_discount_fixed(self):
        """Compute the percentage discount based on the fixed total discount."""
        if self.env.context.get("ignore_discount_onchange"):
            return
        self = self.with_context(ignore_discount_onchange=True)
        self.discount = self._get_discount_from_fixed_discount()

    @api.onchange("discount")
    def _onchange_discount(self):
        """Reset fixed discount when percentage discount is changed."""
        if self.env.context.get("ignore_discount_onchange"):
            return
        self = self.with_context(ignore_discount_onchange=True)
        self.discount_fixed = 0.0

    def _get_discount_from_fixed_discount(self):
        """Calculate the discount percentage from the fixed total discount amount."""
        self.ensure_one()
        currency = self.currency_id or self.company_id.currency_id

        if float_is_zero(self.discount_fixed, precision_rounding=currency.rounding):
            return 0.0

        # Calculate total before discount
        subtotal = self.product_uom_qty * self.price_unit

        if float_is_zero(subtotal, precision_rounding=currency.rounding):
            return 0.0

        # Calculate percentage: (fixed_discount / subtotal) * 100
        return (self.discount_fixed / subtotal) * 100

    def _prepare_invoice_line(self, **optional_values):
        """Transfer fixed discount to invoice line."""
        res = super()._prepare_invoice_line(**optional_values)
        res["discount_fixed"] = self.discount_fixed
        return res
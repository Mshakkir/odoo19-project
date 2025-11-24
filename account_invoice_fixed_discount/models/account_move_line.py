# Copyright 2017 ForgeFlow S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

from odoo import api, fields, models
from odoo.tools.float_utils import float_is_zero


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    discount_fixed = fields.Monetary(
        string="Discount (Fixed)",
        default=0.0,
        currency_field="currency_id",
        help=(
            "Apply a fixed total discount to this line. "
            "This is a total discount amount, not per unit."
        ),
    )

    @api.depends("quantity", "discount", "price_unit", "tax_ids", "currency_id", "discount_fixed")
    def _compute_totals(self):
        """Adjust the computation of the price_subtotal and price_total fields to
        account for the fixed discount amount.

        The fixed discount is applied as a TOTAL discount on the line,
        not multiplied by quantity.
        """
        done_lines = self.env["account.move.line"]
        for line in self:
            if float_is_zero(
                    line.discount_fixed, precision_rounding=line.currency_id.rounding
            ):
                continue

            # Calculate subtotal before discount
            subtotal_before_discount = line.quantity * line.price_unit

            # Apply fixed discount to the total
            subtotal_after_discount = subtotal_before_discount - line.discount_fixed

            # Calculate effective price per unit after discount
            if line.quantity and not float_is_zero(line.quantity, precision_rounding=line.currency_id.rounding):
                effective_price_unit = subtotal_after_discount / line.quantity
            else:
                effective_price_unit = line.price_unit

            if line.tax_ids:
                taxes_res = line.tax_ids.compute_all(
                    effective_price_unit,
                    quantity=line.quantity,
                    currency=line.currency_id,
                    product=line.product_id,
                    partner=line.partner_id,
                    is_refund=line.is_refund,
                )
                line.price_subtotal = taxes_res["total_excluded"]
                line.price_total = taxes_res["total_included"]
            else:
                # No taxes applied on the line.
                line.price_subtotal = subtotal_after_discount
                line.price_total = subtotal_after_discount

            done_lines |= line

        # Compute the regular totals for regular lines.
        return super(AccountMoveLine, self - done_lines)._compute_totals()

    @api.onchange('discount_fixed')
    def _onchange_discount_fixed(self):
        """Compute the percentage discount based on the fixed total discount."""
        if self.env.context.get("ignore_discount_onchange"):
            return

        if self.discount_fixed:
            # Calculate the percentage discount
            calculated_discount = self._get_discount_from_fixed_discount()
            # Set discount with context to prevent triggering _onchange_discount
            self.with_context(ignore_discount_onchange=True).discount = calculated_discount
        else:
            # If fixed discount is cleared, clear the percentage discount too
            self.with_context(ignore_discount_onchange=True).discount = 0.0

    @api.onchange("discount")
    def _onchange_discount(self):
        """Reset fixed discount when percentage discount is changed."""
        if self.env.context.get("ignore_discount_onchange"):
            return

        # Only reset fixed discount if discount percentage is being manually changed
        if self.discount:
            self.with_context(ignore_discount_onchange=True).discount_fixed = 0.0
        else:
            # If discount is cleared, also clear fixed discount
            self.with_context(ignore_discount_onchange=True).discount_fixed = 0.0

    def _get_discount_from_fixed_discount(self):
        """Calculate the discount percentage from the fixed total discount amount."""
        self.ensure_one()
        currency = self.currency_id or self.company_id.currency_id

        if float_is_zero(self.discount_fixed, precision_rounding=currency.rounding):
            return 0.0

        # Calculate total before discount
        subtotal = self.quantity * self.price_unit

        if float_is_zero(subtotal, precision_rounding=currency.rounding):
            return 0.0

        # Calculate percentage: (fixed_discount / subtotal) * 100
        return (self.discount_fixed / subtotal) * 100
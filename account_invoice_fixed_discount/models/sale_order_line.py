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

    def _get_protected_fields(self):
        """Add discount_fixed to protected fields."""
        return super()._get_protected_fields() + ['discount_fixed']

    @api.depends("product_uom_qty", "discount", "price_unit", "discount_fixed")
    def _compute_amount(self):
        """Override to calculate amounts with fixed discount."""
        lines_with_fixed_discount = self.env["sale.order.line"]

        for line in self:
            if float_is_zero(line.discount_fixed, precision_rounding=line.currency_id.rounding):
                continue

            lines_with_fixed_discount |= line

            # Calculate price with fixed discount
            subtotal_before = line.product_uom_qty * line.price_unit

            if line.product_uom_qty:
                subtotal_after = subtotal_before - line.discount_fixed
                effective_price_unit = subtotal_after / line.product_uom_qty
            else:
                effective_price_unit = line.price_unit

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

        # Compute remaining lines normally
        remaining_lines = self - lines_with_fixed_discount
        if remaining_lines:
            super(SaleOrderLine, remaining_lines)._compute_amount()

    @api.onchange("discount_fixed", "price_unit", "product_uom_qty")
    def _onchange_discount_fixed(self):
        if self.env.context.get("ignore_discount_onchange"):
            return
        self = self.with_context(ignore_discount_onchange=True)
        self.discount = self._get_discount_from_fixed_discount()

    @api.onchange("discount")
    def _onchange_discount(self):
        if self.env.context.get("ignore_discount_onchange"):
            return
        self = self.with_context(ignore_discount_onchange=True)
        self.discount_fixed = 0.0

    def _get_discount_from_fixed_discount(self):
        self.ensure_one()
        currency = self.currency_id or self.company_id.currency_id

        if float_is_zero(self.discount_fixed, precision_rounding=currency.rounding):
            return 0.0

        subtotal = self.product_uom_qty * self.price_unit
        if float_is_zero(subtotal, precision_rounding=currency.rounding):
            return 0.0

        return (self.discount_fixed / subtotal) * 100

    def _prepare_invoice_line(self, **optional_values):
        res = super()._prepare_invoice_line(**optional_values)
        res["discount_fixed"] = self.discount_fixed
        return res

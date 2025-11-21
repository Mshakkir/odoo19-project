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

    @api.depends("product_uom_qty", "discount", "price_unit", "tax_id", "discount_fixed")
    def _compute_amount(self):
        """Compute the amounts of the SO line with fixed discount support."""
        done_lines = self.env["sale.order.line"]
        for line in self:
            if float_is_zero(
                line.discount_fixed,
                precision_rounding=line.currency_id.rounding if line.currency_id else 0.01
            ):
                continue

            # Calculate subtotal before discount
            subtotal_before_discount = line.product_uom_qty * line.price_unit

            # Apply fixed discount to the total
            subtotal_after_discount = subtotal_before_discount - line.discount_fixed

            # Calculate effective price per unit after discount
            if line.product_uom_qty and not float_is_zero(
                line.product_uom_qty,
                precision_rounding=line.currency_id.rounding if line.currency_id else 0.01
            ):
                effective_price_unit = subtotal_after_discount / line.product_uom_qty
            else:
                effective_price_unit = line.price_unit

            if line.tax_id:
                taxes = line.tax_id.compute_all(
                    effective_price_unit,
                    line.order_id.currency_id,
                    line.product_uom_qty,
                    product=line.product_id,
                    partner=line.order_id.partner_shipping_id,
                )
                line.price_tax = taxes["total_included"] - taxes["total_excluded"]
                line.price_total = taxes["total_included"]
                line.price_subtotal = taxes["total_excluded"]
            else:
                line.price_tax = 0.0
                line.price_total = subtotal_after_discount
                line.price_subtotal = subtotal_after_discount

            done_lines |= line

        return super(SaleOrderLine, self - done_lines)._compute_amount()

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
        currency = self.currency_id or self.order_id.currency_id or self.company_id.currency_id

        rounding = currency.rounding if currency else 0.01

        if float_is_zero(self.discount_fixed, precision_rounding=rounding):
            return 0.0

        subtotal = self.product_uom_qty * self.price_unit

        if float_is_zero(subtotal, precision_rounding=rounding):
            return 0.0

        return (self.discount_fixed / subtotal) * 100

    def _prepare_invoice_line(self, **optional_values):
        """Pass the fixed discount to the invoice line."""
        res = super()._prepare_invoice_line(**optional_values)
        res["discount_fixed"] = self.discount_fixed
        return res
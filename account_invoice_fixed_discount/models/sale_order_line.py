# # # Copyright 2017 ForgeFlow S.L.
# # # License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)
# #
# # from odoo import api, fields, models
# # from odoo.tools.float_utils import float_is_zero
# #
# #
# # class SaleOrderLine(models.Model):
# #     _inherit = "sale.order.line"
# #
# #     discount_fixed = fields.Monetary(
# #         string="Disc(Fixed)",
# #         default=0.0,
# #         currency_field="currency_id",
# #         help=(
# #             "Apply a fixed total discount to this line. "
# #             "This is a total discount amount, not per unit."
# #         ),
# #     )
# #
# #     # NEW FIELD: Amount before any discount
# #     price_subtotal_before_discount = fields.Monetary(
# #         string="Amount(Before Disc)",
# #         compute="_compute_amount_before_discount",
# #         store=True,
# #         currency_field="currency_id",
# #     )
# #
# #     @api.depends("product_uom_qty", "price_unit")
# #     def _compute_amount_before_discount(self):
# #         """Calculate the amount before any discount is applied."""
# #         for line in self:
# #             line.price_subtotal_before_discount = line.product_uom_qty * line.price_unit
# #
# #     @api.depends("product_uom_qty", "discount", "price_unit", "tax_ids", "discount_fixed")
# #     def _compute_amount(self):
# #         """Compute the amounts of the SO line with fixed discount support."""
# #         for line in self:
# #             # Check if we have a fixed discount
# #             has_fixed_discount = line.discount_fixed and not float_is_zero(
# #                 line.discount_fixed,
# #                 precision_rounding=line.currency_id.rounding if line.currency_id else 0.01
# #             )
# #
# #             if has_fixed_discount:
# #                 # Calculate subtotal before discount
# #                 subtotal_before_discount = line.product_uom_qty * line.price_unit
# #
# #                 # Apply fixed discount to the total
# #                 subtotal_after_discount = subtotal_before_discount - line.discount_fixed
# #
# #                 # Calculate effective price per unit after discount
# #                 if line.product_uom_qty and not float_is_zero(
# #                         line.product_uom_qty,
# #                         precision_rounding=line.currency_id.rounding if line.currency_id else 0.01
# #                 ):
# #                     effective_price_unit = subtotal_after_discount / line.product_uom_qty
# #                 else:
# #                     effective_price_unit = line.price_unit
# #
# #                 if line.tax_ids:
# #                     taxes = line.tax_ids.compute_all(
# #                         effective_price_unit,
# #                         line.order_id.currency_id,
# #                         line.product_uom_qty,
# #                         product=line.product_id,
# #                         partner=line.order_id.partner_shipping_id,
# #                     )
# #                     line.price_tax = taxes["total_included"] - taxes["total_excluded"]
# #                     line.price_total = taxes["total_included"]
# #                     line.price_subtotal = taxes["total_excluded"]
# #                 else:
# #                     line.price_tax = 0.0
# #                     line.price_total = subtotal_after_discount
# #                     line.price_subtotal = subtotal_after_discount
# #             else:
# #                 # Use standard Odoo computation for lines without fixed discount
# #                 super(SaleOrderLine, line)._compute_amount()
# #
# #     @api.onchange('discount_fixed', 'price_unit', 'product_uom_qty')
# #     def _onchange_discount_fixed(self):
# #         """Auto-calculate and display the percentage discount when fixed discount is entered."""
# #         currency = self.currency_id or self.order_id.currency_id or self.company_id.currency_id
# #
# #         # Check if discount_fixed is zero or empty
# #         if not self.discount_fixed or float_is_zero(
# #                 self.discount_fixed,
# #                 precision_rounding=currency.rounding if currency else 0.01
# #         ):
# #             # Clear the percentage discount when fixed discount is removed
# #             self.discount = 0.0
# #             # Force recalculation by calling compute
# #             self._compute_amount()
# #             return
# #
# #         # Calculate the percentage discount for display purposes
# #         calculated_discount = self._get_discount_from_fixed_discount()
# #         # Update discount percentage WITHOUT clearing discount_fixed
# #         self.discount = calculated_discount
# #         # Force recalculation
# #         self._compute_amount()
# #
# #     def _get_discount_from_fixed_discount(self):
# #         """Calculate the discount percentage from the fixed total discount amount."""
# #         self.ensure_one()
# #         currency = self.currency_id or self.order_id.currency_id or self.company_id.currency_id
# #
# #         rounding = currency.rounding if currency else 0.01
# #
# #         if float_is_zero(self.discount_fixed, precision_rounding=rounding):
# #             return 0.0
# #
# #         subtotal = self.product_uom_qty * self.price_unit
# #
# #         if float_is_zero(subtotal, precision_rounding=rounding):
# #             return 0.0
# #
# #         return (self.discount_fixed / subtotal) * 100
# #
# #     def _prepare_invoice_line(self, **optional_values):
# #         """Pass the fixed discount to the invoice line."""
# #         res = super()._prepare_invoice_line(**optional_values)
# #         res["discount_fixed"] = self.discount_fixed
# #         return res
#
#
# # Copyright 2017 ForgeFlow S.L.
# # License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)
#
# from odoo import api, fields, models
# from odoo.tools.float_utils import float_is_zero
#
#
# class SaleOrderLine(models.Model):
#     _inherit = "sale.order.line"
#
#     discount_fixed = fields.Monetary(
#         string="Disc(Fixed)",
#         default=0.0,
#         currency_field="currency_id",
#         help=(
#             "Apply a fixed total discount to this line. "
#             "This is a total discount amount, not per unit."
#         ),
#     )
#
#     # NEW FIELD: Amount before any discount
#     price_subtotal_before_discount = fields.Monetary(
#         string="Amount(Before Disc)",
#         compute="_compute_amount_before_discount",
#         store=True,
#         currency_field="currency_id",
#     )
#
#     # NEW FIELD: VAT Amount before any discount
#     price_tax_before_discount = fields.Monetary(
#         string="VAT Amount(Before Disc)",
#         compute="_compute_tax_before_discount",
#         store=True,
#         currency_field="currency_id",
#     )
#
#     @api.depends("product_uom_qty", "price_unit")
#     def _compute_amount_before_discount(self):
#         """Calculate the amount before any discount is applied."""
#         for line in self:
#             line.price_subtotal_before_discount = line.product_uom_qty * line.price_unit
#
#     @api.depends("product_uom_qty", "price_unit", "tax_ids")
#     def _compute_tax_before_discount(self):
#         """Calculate the tax amount before any discount is applied."""
#         for line in self:
#             if line.tax_ids:
#                 # Calculate tax on original price (before discount)
#                 taxes = line.tax_ids.compute_all(
#                     line.price_unit,
#                     line.order_id.currency_id,
#                     line.product_uom_qty,
#                     product=line.product_id,
#                     partner=line.order_id.partner_shipping_id,
#                 )
#                 line.price_tax_before_discount = taxes["total_included"] - taxes["total_excluded"]
#             else:
#                 line.price_tax_before_discount = 0.0
#
#     @api.depends("product_uom_qty", "discount", "price_unit", "tax_ids", "discount_fixed")
#     def _compute_amount(self):
#         """Compute the amounts of the SO line with fixed discount support."""
#         for line in self:
#             # Check if we have a fixed discount
#             has_fixed_discount = line.discount_fixed and not float_is_zero(
#                 line.discount_fixed,
#                 precision_rounding=line.currency_id.rounding if line.currency_id else 0.01
#             )
#
#             if has_fixed_discount:
#                 # Calculate subtotal before discount
#                 subtotal_before_discount = line.product_uom_qty * line.price_unit
#
#                 # Apply fixed discount to the total
#                 subtotal_after_discount = subtotal_before_discount - line.discount_fixed
#
#                 # Calculate effective price per unit after discount
#                 if line.product_uom_qty and not float_is_zero(
#                         line.product_uom_qty,
#                         precision_rounding=line.currency_id.rounding if line.currency_id else 0.01
#                 ):
#                     effective_price_unit = subtotal_after_discount / line.product_uom_qty
#                 else:
#                     effective_price_unit = line.price_unit
#
#                 if line.tax_ids:
#                     taxes = line.tax_ids.compute_all(
#                         effective_price_unit,
#                         line.order_id.currency_id,
#                         line.product_uom_qty,
#                         product=line.product_id,
#                         partner=line.order_id.partner_shipping_id,
#                     )
#                     line.price_tax = taxes["total_included"] - taxes["total_excluded"]
#                     line.price_total = taxes["total_included"]
#                     line.price_subtotal = taxes["total_excluded"]
#                 else:
#                     line.price_tax = 0.0
#                     line.price_total = subtotal_after_discount
#                     line.price_subtotal = subtotal_after_discount
#             else:
#                 # Use standard Odoo computation for lines without fixed discount
#                 super(SaleOrderLine, line)._compute_amount()
#
#     @api.onchange('discount_fixed', 'price_unit', 'product_uom_qty')
#     def _onchange_discount_fixed(self):
#         """Auto-calculate and display the percentage discount when fixed discount is entered."""
#         currency = self.currency_id or self.order_id.currency_id or self.company_id.currency_id
#
#         # Check if discount_fixed is zero or empty
#         if not self.discount_fixed or float_is_zero(
#                 self.discount_fixed,
#                 precision_rounding=currency.rounding if currency else 0.01
#         ):
#             # Clear the percentage discount when fixed discount is removed
#             self.discount = 0.0
#             # Force recalculation by calling compute
#             self._compute_amount()
#             return
#
#         # Calculate the percentage discount for display purposes
#         calculated_discount = self._get_discount_from_fixed_discount()
#         # Update discount percentage WITHOUT clearing discount_fixed
#         self.discount = calculated_discount
#         # Force recalculation
#         self._compute_amount()
#
#     def _get_discount_from_fixed_discount(self):
#         """Calculate the discount percentage from the fixed total discount amount."""
#         self.ensure_one()
#         currency = self.currency_id or self.order_id.currency_id or self.company_id.currency_id
#
#         rounding = currency.rounding if currency else 0.01
#
#         if float_is_zero(self.discount_fixed, precision_rounding=rounding):
#             return 0.0
#
#         subtotal = self.product_uom_qty * self.price_unit
#
#         if float_is_zero(subtotal, precision_rounding=rounding):
#             return 0.0
#
#         return (self.discount_fixed / subtotal) * 100
#
#     def _prepare_invoice_line(self, **optional_values):
#         """Pass the fixed discount to the invoice line."""
#         res = super()._prepare_invoice_line(**optional_values)
#         res["discount_fixed"] = self.discount_fixed
#         return res


# Copyright 2017 ForgeFlow S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

from odoo import api, fields, models
from odoo.tools.float_utils import float_is_zero


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    discount_fixed = fields.Monetary(
        string="Disc(Fixed)",
        default=0.0,
        currency_field="currency_id",
        help=(
            "Apply a fixed total discount to this line. "
            "This is a total discount amount, not per unit."
        ),
    )

    # NEW FIELD: Amount before any discount
    price_subtotal_before_discount = fields.Monetary(
        string="Amount(Before Disc)",
        compute="_compute_amount_before_discount",
        store=True,
        currency_field="currency_id",
    )

    # NEW FIELD: VAT Amount before any discount
    price_tax_before_discount = fields.Monetary(
        string="VAT Amount(Before Disc)",
        compute="_compute_tax_before_discount",
        store=True,
        currency_field="currency_id",
    )

    @api.depends("product_uom_qty", "price_unit")
    def _compute_amount_before_discount(self):
        """Calculate the amount before any discount is applied."""
        for line in self:
            line.price_subtotal_before_discount = line.product_uom_qty * line.price_unit

    @api.depends("product_uom_qty", "price_unit", "tax_ids")
    def _compute_tax_before_discount(self):
        """Calculate the tax amount before any discount is applied."""
        for line in self:
            if line.tax_ids:
                # Calculate tax on original price (before discount)
                taxes = line.tax_ids.compute_all(
                    line.price_unit,
                    line.order_id.currency_id,
                    line.product_uom_qty,
                    product=line.product_id,
                    partner=line.order_id.partner_shipping_id,
                )
                line.price_tax_before_discount = taxes["total_included"] - taxes["total_excluded"]
            else:
                line.price_tax_before_discount = 0.0

    @api.depends("product_uom_qty", "discount", "price_unit", "tax_ids", "discount_fixed")
    def _compute_amount(self):
        """Compute the amounts of the SO line with fixed discount support."""
        for line in self:
            # Check if we have a fixed discount
            has_fixed_discount = line.discount_fixed and not float_is_zero(
                line.discount_fixed,
                precision_rounding=line.currency_id.rounding if line.currency_id else 0.01
            )

            if has_fixed_discount:
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

                if line.tax_ids:
                    taxes = line.tax_ids.compute_all(
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
            else:
                # Use standard Odoo computation for lines without fixed discount
                super(SaleOrderLine, line)._compute_amount()

    @api.onchange('discount_fixed', 'price_unit', 'product_uom_qty')
    def _onchange_discount_fixed(self):
        """Auto-calculate and display the percentage discount when fixed discount is entered."""
        currency = self.currency_id or self.order_id.currency_id or self.company_id.currency_id

        # Check if discount_fixed is zero or empty
        if not self.discount_fixed or float_is_zero(
                self.discount_fixed,
                precision_rounding=currency.rounding if currency else 0.01
        ):
            # Clear the percentage discount when fixed discount is removed
            self.discount = 0.0
            # Force recalculation by calling compute
            self._compute_amount()
            return

        # Calculate the percentage discount for display purposes
        calculated_discount = self._get_discount_from_fixed_discount()
        # Update discount percentage WITHOUT clearing discount_fixed
        self.discount = calculated_discount
        # Force recalculation
        self._compute_amount()

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
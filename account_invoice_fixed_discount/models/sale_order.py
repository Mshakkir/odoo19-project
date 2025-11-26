# # Copyright 2017 ForgeFlow S.L.
# # License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)
#
# from odoo import api, fields, models
# from odoo.tools.float_utils import float_is_zero
#
#
# class SaleOrder(models.Model):
#     _inherit = "sale.order"
#
#     global_discount_fixed = fields.Monetary(
#         string="Global Discount (Fixed)",
#         default=0.0,
#         currency_field="currency_id",
#         help="Apply a fixed discount to the entire order. This will be distributed proportionally across all order lines.",
#         tracking=True,
#     )
#
#     @api.onchange('global_discount_fixed')
#     def _onchange_global_discount_fixed(self):
#         """Distribute the global discount proportionally across all order lines."""
#         if not self.order_line:
#             return
#
#         currency = self.currency_id or self.company_id.currency_id
#
#         if float_is_zero(self.global_discount_fixed, precision_rounding=currency.rounding):
#             # Clear individual line discounts if global discount is removed
#             for line in self.order_line:
#                 line.discount_fixed = 0.0
#                 line.discount = 0.0
#                 # Trigger recomputation to reset amounts
#                 line._compute_amount()
#             return
#
#         # Calculate total before any discount
#         total_before_discount = sum(line.product_uom_qty * line.price_unit for line in self.order_line)
#
#         if float_is_zero(total_before_discount, precision_rounding=currency.rounding):
#             return
#
#         # Distribute global discount proportionally
#         for line in self.order_line:
#             line_subtotal = line.product_uom_qty * line.price_unit
#             if not float_is_zero(line_subtotal, precision_rounding=currency.rounding):
#                 # Calculate proportional discount for this line
#                 line_proportion = line_subtotal / total_before_discount
#                 line.discount_fixed = self.global_discount_fixed * line_proportion
#                 # Trigger the onchange to update discount percentage and amounts
#                 line._onchange_discount_fixed()
#
#     def write(self, vals):
#         """Ensure global discount is applied when saving."""
#         res = super().write(vals)
#
#         # If global_discount_fixed is being updated, trigger the distribution
#         if 'global_discount_fixed' in vals:
#             for order in self:
#                 order._onchange_global_discount_fixed()
#                 # Force recalculation of order totals
#                 order.order_line._compute_amount()
#
#         return res
#
#     @api.model_create_multi
#     def create(self, vals_list):
#         """Ensure global discount is applied when creating."""
#         orders = super().create(vals_list)
#
#         for order in orders:
#             if order.global_discount_fixed:
#                 order._onchange_global_discount_fixed()
#                 # Force recalculation of order totals
#                 order.order_line._compute_amount()
#
#         return orders
#
#     def _prepare_invoice(self):
#         """Pass the global discount to the invoice."""
#         res = super()._prepare_invoice()
#         res['global_discount_fixed'] = self.global_discount_fixed
#         return res

# Copyright 2017 ForgeFlow S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

# Copyright 2017 ForgeFlow S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

# Copyright 2017 ForgeFlow S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

# from odoo import api, fields, models
# import logging
#
# _logger = logging.getLogger(__name__)
#
#
# class SaleOrder(models.Model):
#     _inherit = "sale.order"
#
#     global_discount_fixed = fields.Monetary(
#         string="Global Discount (Fixed)",
#         default=0.0,
#         currency_field="currency_id",
#         tracking=True,
#     )
#
#     amount_undiscounted = fields.Monetary(
#         string='Amount Undiscounted',
#         compute='_compute_amounts_with_discount',
#         store=True,
#         currency_field='currency_id'
#     )
#
#     amount_after_discount = fields.Monetary(
#         string='Amount After Discount',
#         compute='_compute_amounts_with_discount',
#         store=True,
#         currency_field='currency_id'
#     )
#
#     @api.depends('order_line.price_subtotal', 'global_discount_fixed')
#     def _compute_amounts_with_discount(self):
#         """Calculate amounts before and after global discount."""
#         for order in self:
#             amount_undiscounted = sum(order.order_line.mapped('price_subtotal'))
#             order.amount_undiscounted = amount_undiscounted
#             order.amount_after_discount = amount_undiscounted - order.global_discount_fixed
#             _logger.info(f"=== DISCOUNT DEBUG ===")
#             _logger.info(
#                 f"Untaxed: {amount_undiscounted}, Discount: {order.global_discount_fixed}, After: {order.amount_after_discount}")
#
#     @api.depends('order_line.price_total', 'order_line.price_subtotal', 'global_discount_fixed')
#     def _compute_amounts(self):
#         """Override the main compute amounts method."""
#         _logger.info("=== _compute_amounts called ===")
#
#         for order in self:
#             order_lines = order.order_line.filtered(lambda x: not x.display_type)
#
#             # Calculate base amounts from lines
#             amount_untaxed = sum(order_lines.mapped('price_subtotal'))
#             amount_tax = sum(order_lines.mapped('price_tax'))
#
#             _logger.info(f"Original - Untaxed: {amount_untaxed}, Tax: {amount_tax}")
#
#             # Apply discount
#             if order.global_discount_fixed > 0:
#                 amount_untaxed_after_discount = amount_untaxed - order.global_discount_fixed
#
#                 # Recalculate tax proportionally
#                 if amount_untaxed > 0:
#                     discount_ratio = amount_untaxed_after_discount / amount_untaxed
#                     amount_tax = amount_tax * discount_ratio
#
#                 _logger.info(
#                     f"After Discount - Untaxed: {amount_untaxed_after_discount}, Tax: {amount_tax}, Total: {amount_untaxed_after_discount + amount_tax}")
#
#                 order.update({
#                     'amount_untaxed': amount_untaxed_after_discount,
#                     'amount_tax': amount_tax,
#                     'amount_total': amount_untaxed_after_discount + amount_tax,
#                 })
#             else:
#                 order.update({
#                     'amount_untaxed': amount_untaxed,
#                     'amount_tax': amount_tax,
#                     'amount_total': amount_untaxed + amount_tax,
#                 })
#
#     def _prepare_invoice(self):
#         """Pass the global discount to the invoice."""
#         res = super()._prepare_invoice()
#         res['global_discount_fixed'] = self.global_discount_fixed
#         return res


# correctly working in sale order and quotation
from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    global_discount_fixed = fields.Monetary(
        string="Global Discount (Fixed)",
        default=0.0,
        currency_field="currency_id",
        tracking=True,
    )

    amount_undiscounted = fields.Monetary(
        string='Amount Undiscounted',
        compute='_compute_amounts_with_discount',
        store=True,
        currency_field='currency_id'
    )

    amount_after_discount = fields.Monetary(
        string='Amount After Discount',
        compute='_compute_amounts_with_discount',
        store=True,
        currency_field='currency_id'
    )

    @api.depends('order_line.price_subtotal', 'global_discount_fixed')
    def _compute_amounts_with_discount(self):
        """Calculate amounts before and after global discount."""
        for order in self:
            amount_undiscounted = sum(order.order_line.mapped('price_subtotal'))
            order.amount_undiscounted = amount_undiscounted
            order.amount_after_discount = amount_undiscounted - order.global_discount_fixed
            _logger.info(f"=== SALE ORDER DISCOUNT DEBUG ===")
            _logger.info(
                f"Untaxed: {amount_undiscounted}, Discount: {order.global_discount_fixed}, After: {order.amount_after_discount}")

    @api.depends('order_line.price_total', 'order_line.price_subtotal', 'global_discount_fixed')
    def _compute_amounts(self):
        """Override the main compute amounts method."""
        _logger.info("=== SALE ORDER _compute_amounts called ===")

        for order in self:
            order_lines = order.order_line.filtered(lambda x: not x.display_type)

            # Calculate base amounts from lines
            amount_untaxed = sum(order_lines.mapped('price_subtotal'))
            amount_tax = sum(order_lines.mapped('price_tax'))

            _logger.info(f"Original - Untaxed: {amount_untaxed}, Tax: {amount_tax}")

            # Apply discount
            if order.global_discount_fixed > 0:
                amount_untaxed_after_discount = amount_untaxed - order.global_discount_fixed

                # Recalculate tax proportionally
                if amount_untaxed > 0:
                    discount_ratio = amount_untaxed_after_discount / amount_untaxed
                    amount_tax = amount_tax * discount_ratio

                _logger.info(
                    f"After Discount - Untaxed: {amount_untaxed_after_discount}, Tax: {amount_tax}, Total: {amount_untaxed_after_discount + amount_tax}")

                order.update({
                    'amount_untaxed': amount_untaxed_after_discount,
                    'amount_tax': amount_tax,
                    'amount_total': amount_untaxed_after_discount + amount_tax,
                })
            else:
                order.update({
                    'amount_untaxed': amount_untaxed,
                    'amount_tax': amount_tax,
                    'amount_total': amount_untaxed + amount_tax,
                })

    def _prepare_invoice(self):
        """Pass the global discount to the invoice."""
        invoice_vals = super()._prepare_invoice()

        # Add the global discount
        invoice_vals['global_discount_fixed'] = self.global_discount_fixed

        _logger.info(f"=== PREPARING INVOICE ===")
        _logger.info(f"Passing discount to invoice: {self.global_discount_fixed}")

        return invoice_vals


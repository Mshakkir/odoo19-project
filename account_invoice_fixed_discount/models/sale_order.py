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

from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    global_discount_fixed = fields.Monetary(
        string='Global Discount (Fixed)',
        currency_field='currency_id',
        default=0.0,
        help="Fixed discount amount applied to the entire order"
    )

    amount_untaxed_before_discount = fields.Monetary(
        string='Untaxed Amount (Before Discount)',
        compute='_compute_discount_amounts',
        store=True,
        currency_field='currency_id'
    )

    amount_discount = fields.Monetary(
        string='Discount Amount',
        compute='_compute_discount_amounts',
        store=True,
        currency_field='currency_id'
    )

    amount_untaxed_after_discount = fields.Monetary(
        string='Untaxed Amount (After Discount)',
        compute='_compute_discount_amounts',
        store=True,
        currency_field='currency_id'
    )

    @api.depends('order_line.price_subtotal', 'order_line.price_total', 'global_discount_fixed')
    def _compute_discount_amounts(self):
        for order in self:
            # Get sum of all line subtotals (before discount)
            amount_untaxed = sum(line.price_subtotal for line in order.order_line)
            amount_tax = sum(line.price_tax for line in order.order_line)

            # Store amounts
            order.amount_untaxed_before_discount = amount_untaxed
            order.amount_discount = order.global_discount_fixed or 0.0

            # Calculate after discount
            amount_after_discount = amount_untaxed - order.amount_discount
            order.amount_untaxed_after_discount = amount_after_discount

    @api.depends('order_line.price_total', 'global_discount_fixed')
    def _compute_amounts(self):
        """Override the compute method to apply discount"""
        super()._compute_amounts()
        for order in self:
            if order.global_discount_fixed:
                # Recalculate amounts with discount
                amount_untaxed = sum(line.price_subtotal for line in order.order_line)
                amount_tax = sum(line.price_tax for line in order.order_line)

                # Apply discount to untaxed amount
                discount = order.global_discount_fixed
                amount_untaxed_discounted = amount_untaxed - discount

                # Adjust tax proportionally
                if amount_untaxed > 0:
                    tax_ratio = amount_untaxed_discounted / amount_untaxed
                    amount_tax = amount_tax * tax_ratio

                # Update order amounts
                order.update({
                    'amount_untaxed': amount_untaxed_discounted,
                    'amount_tax': amount_tax,
                    'amount_total': amount_untaxed_discounted + amount_tax,
                })
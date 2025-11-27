# Copyright 2017 ForgeFlow S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

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

# models/sale_order.py

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    # Global discount as separate field (NOT distributed to lines)
    global_discount_type = fields.Selection([
        ('fixed', 'Fixed Amount'),
        ('percent', 'Percentage'),
    ], string="Global Discount Type", default='fixed')

    global_discount_fixed = fields.Monetary(
        string="Global Discount",
        currency_field="currency_id",
        default=0.0,
        help="Global discount applied to entire order (not distributed to lines)"
    )

    global_discount_percent = fields.Float(
        string="Global Discount %",
        default=0.0,
    )

    # Computed amounts
    amount_before_global_discount = fields.Monetary(
        string="Amount Before Global Discount",
        compute="_compute_global_discount_amounts",
        store=True,
        currency_field="currency_id",
    )

    global_discount_amount = fields.Monetary(
        string="Global Discount Amount",
        compute="_compute_global_discount_amounts",
        store=True,
        currency_field="currency_id",
    )

    @api.depends('order_line.price_subtotal', 'global_discount_type',
                 'global_discount_fixed', 'global_discount_percent')
    def _compute_global_discount_amounts(self):
        """Calculate global discount without modifying line items"""
        for order in self:
            # Get subtotal from lines (UNCHANGED)
            subtotal = sum(order.order_line.mapped('price_subtotal'))
            order.amount_before_global_discount = subtotal

            # Calculate global discount
            if order.global_discount_type == 'fixed':
                order.global_discount_amount = order.global_discount_fixed
            else:  # percentage
                order.global_discount_amount = subtotal * (order.global_discount_percent / 100)

    @api.depends('amount_untaxed', 'amount_tax', 'global_discount_amount')
    def _compute_amount_total(self):
        """Override total to include global discount"""
        for order in self:
            # Standard Odoo calculation
            super(SaleOrder, order)._compute_amount_total()

            # Apply global discount to final total
            order.amount_total = order.amount_total - order.global_discount_amount

    def _prepare_invoice(self):
        """Pass global discount to invoice without modifying lines"""
        invoice_vals = super()._prepare_invoice()
        invoice_vals.update({
            'global_discount_type': self.global_discount_type,
            'global_discount_fixed': self.global_discount_fixed,
            'global_discount_percent': self.global_discount_percent,
        })
        return invoice_vals

# Key Points:
# ✓ Order lines remain UNCHANGED
# ✓ Global discount tracked separately
# ✓ Total calculation includes global discount
# ✓ Reporting shows TRUE product prices
# ✓ Analytics remain accurate
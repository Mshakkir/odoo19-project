# Copyright 2017 ForgeFlow S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

# from odoo import api, fields, models
# from odoo.tools.float_utils import float_is_zero
#
#
# class AccountMove(models.Model):
#     _inherit = "account.move"
#
#     global_discount_fixed = fields.Monetary(
#         string="Global Discount (Fixed)",
#         default=0.0,
#         currency_field="currency_id",
#         help="Apply a fixed discount to the entire invoice. This will be distributed proportionally across all invoice lines.",
#         tracking=True,
#         states={'posted': [('readonly', True)]},
#     )
#
#     @api.onchange('global_discount_fixed')
#     def _onchange_global_discount_fixed(self):
#         """Distribute the global discount proportionally across all invoice lines."""
#         if not self.invoice_line_ids:
#             return
#
#         currency = self.currency_id or self.company_id.currency_id
#
#         if float_is_zero(self.global_discount_fixed, precision_rounding=currency.rounding):
#             # Clear individual line discounts if global discount is removed
#             for line in self.invoice_line_ids.filtered(lambda l: not l.display_type):
#                 line.discount_fixed = 0.0
#                 line.discount = 0.0
#                 # Trigger recomputation to reset amounts
#                 line._compute_totals()
#             return
#
#         # Calculate total before any discount (only for product lines)
#         product_lines = self.invoice_line_ids.filtered(lambda l: not l.display_type)
#         total_before_discount = sum(line.quantity * line.price_unit for line in product_lines)
#
#         if float_is_zero(total_before_discount, precision_rounding=currency.rounding):
#             return
#
#         # Distribute global discount proportionally
#         for line in product_lines:
#             line_subtotal = line.quantity * line.price_unit
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
#             for move in self:
#                 if move.state != 'posted':  # Only apply if not posted
#                     move._onchange_global_discount_fixed()
#                     # Force recalculation of invoice totals
#                     product_lines = move.invoice_line_ids.filtered(lambda l: not l.display_type)
#                     product_lines._compute_totals()
#
#         return res
#
#     @api.model_create_multi
#     def create(self, vals_list):
#         """Ensure global discount is applied when creating."""
#         moves = super().create(vals_list)
#
#         for move in moves:
#             if move.global_discount_fixed and move.state != 'posted':
#                 move._onchange_global_discount_fixed()
#                 # Force recalculation of invoice totals
#                 product_lines = move.invoice_line_ids.filtered(lambda l: not l.display_type)
#                 product_lines._compute_totals()
#
#         return moves

# Copyright 2017 ForgeFlow S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

# Copyright 2017 ForgeFlow S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

# Simpler version - distributes discount to lines
# from odoo import api, fields, models
# import logging
#
# _logger = logging.getLogger(__name__)
#
#
# class AccountMove(models.Model):
#     _inherit = "account.move"
#
#     global_discount_fixed = fields.Monetary(
#         string="Global Discount (Fixed)",
#         default=0.0,
#         currency_field="currency_id",
#         tracking=True,
#         readonly=False,
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
#     @api.depends('invoice_line_ids.price_subtotal', 'global_discount_fixed')
#     def _compute_amounts_with_discount(self):
#         for move in self:
#             if move.is_invoice():
#                 amount_undiscounted = sum(move.invoice_line_ids.mapped('price_subtotal'))
#                 move.amount_undiscounted = amount_undiscounted
#                 move.amount_after_discount = amount_undiscounted - move.global_discount_fixed
#             else:
#                 move.amount_undiscounted = 0.0
#                 move.amount_after_discount = 0.0
#
#     @api.onchange('global_discount_fixed')
#     def _onchange_global_discount_fixed(self):
#         """Distribute discount to invoice lines."""
#         if not self.invoice_line_ids or not self.is_invoice():
#             return
#
#         if self.global_discount_fixed and self.global_discount_fixed > 0:
#             # Calculate total before discount
#             total_before_discount = sum(
#                 line.quantity * line.price_unit
#                 for line in self.invoice_line_ids
#             )
#
#             if total_before_discount > 0:
#                 # Distribute proportionally
#                 for line in self.invoice_line_ids:
#                     line_subtotal = line.quantity * line.price_unit
#                     if line_subtotal > 0:
#                         line_proportion = line_subtotal / total_before_discount
#                         line_discount = self.global_discount_fixed * line_proportion
#
#                         # Calculate discount percentage
#                         if line.price_unit > 0:
#                             discount_pct = (line_discount / (line.quantity * line.price_unit)) * 100
#                             line.discount = discount_pct
#         else:
#             # Clear discounts
#             for line in self.invoice_line_ids:
#                 line.discount = 0.0

# Copyright 2017 ForgeFlow S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

# Copyright 2017 ForgeFlow S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

# Copyright 2017 ForgeFlow S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    global_discount_fixed = fields.Monetary(
        string="Global Discount (Fixed)",
        default=0.0,
        currency_field="currency_id",
        tracking=True,
        readonly=False,
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

    @api.depends('invoice_line_ids.price_subtotal', 'global_discount_fixed')
    def _compute_amounts_with_discount(self):
        """Calculate amounts before and after global discount."""
        for move in self:
            if move.is_invoice():
                amount_undiscounted = sum(move.invoice_line_ids.mapped('price_subtotal'))
                move.amount_undiscounted = amount_undiscounted
                move.amount_after_discount = amount_undiscounted - move.global_discount_fixed
            else:
                move.amount_undiscounted = 0.0
                move.amount_after_discount = 0.0

    def _compute_amount(self):
        """Override to apply global discount and recalculate taxes."""
        # First, call the parent to do the standard computation
        super()._compute_amount()

        # Then apply our discount adjustments
        for move in self:
            if move.is_invoice() and move.global_discount_fixed and move.global_discount_fixed > 0:

                # Get the already computed amounts from parent
                original_untaxed = move.amount_untaxed
                original_tax = move.amount_tax

                _logger.info(f"=== INVOICE COMPUTE ===")
                _logger.info(
                    f"Original - Untaxed: {original_untaxed}, Tax: {original_tax}, Discount: {move.global_discount_fixed}")

                if original_untaxed > 0:
                    # Apply discount to untaxed amount
                    new_untaxed = original_untaxed - move.global_discount_fixed

                    # Recalculate tax proportionally
                    discount_ratio = new_untaxed / original_untaxed
                    new_tax = original_tax * discount_ratio

                    _logger.info(
                        f"After Discount - Untaxed: {new_untaxed}, Tax: {new_tax}, Total: {new_untaxed + new_tax}")

                    # Update move amounts
                    move.amount_untaxed = new_untaxed
                    move.amount_tax = new_tax
                    move.amount_total = new_untaxed + new_tax
                    move.amount_residual = move.amount_total - move.amount_paid
                    move.amount_untaxed_signed = new_untaxed * (
                        -1 if move.move_type in ('in_invoice', 'out_refund') else 1
                    )
                    move.amount_total_signed = move.amount_total * (
                        -1 if move.move_type in ('in_invoice', 'out_refund') else 1
                    )
                    move.amount_total_in_currency_signed = move.amount_total * move.direction_sign
                    move.amount_residual_signed = move.amount_residual * move.direction_sign

    @api.onchange('global_discount_fixed')
    def _onchange_global_discount_fixed(self):
        """Trigger recomputation when discount changes."""
        if self.is_invoice():
            self._compute_amount()
            self._compute_amounts_with_discount()

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to ensure discount is applied on invoice creation."""
        moves = super().create(vals_list)

        for move in moves:
            if move.is_invoice() and move.global_discount_fixed and move.global_discount_fixed > 0:
                _logger.info(f"=== INVOICE CREATED with discount: {move.global_discount_fixed} ===")
                # Trigger recomputation
                move._compute_amount()
                move._compute_amounts_with_discount()

        return moves

    def write(self, vals):
        """Override write to recompute when discount changes."""
        res = super().write(vals)

        if 'global_discount_fixed' in vals:
            for move in self:
                if move.is_invoice():
                    _logger.info(f"=== INVOICE UPDATED with discount: {move.global_discount_fixed} ===")
                    move._compute_amount()
                    move._compute_amounts_with_discount()

        return res
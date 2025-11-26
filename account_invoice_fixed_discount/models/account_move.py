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

# Copyright 2017 ForgeFlow S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

# in jayarajkpkp@gmail cloude ai last answer

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
#         """Calculate amounts before and after global discount."""
#         for move in self:
#             if move.is_invoice():
#                 amount_undiscounted = sum(move.invoice_line_ids.mapped('price_subtotal'))
#                 move.amount_undiscounted = amount_undiscounted
#                 move.amount_after_discount = amount_undiscounted - move.global_discount_fixed
#             else:
#                 move.amount_undiscounted = 0.0
#                 move.amount_after_discount = 0.0
#
#     @api.onchange('global_discount_fixed', 'invoice_line_ids')
#     def _onchange_global_discount_fixed(self):
#         """Apply discount proportionally to invoice lines."""
#         if not self.is_invoice() or not self.invoice_line_ids:
#             return
#
#         if self.global_discount_fixed and self.global_discount_fixed > 0:
#             # Calculate total before discount (without any existing line discounts)
#             total_before_discount = 0.0
#             for line in self.invoice_line_ids:
#                 if not line.display_type:
#                     # Calculate original price without discount
#                     total_before_discount += line.quantity * line.price_unit
#
#             if total_before_discount > 0:
#                 # Distribute discount proportionally to each line
#                 for line in self.invoice_line_ids:
#                     if not line.display_type:
#                         line_subtotal = line.quantity * line.price_unit
#                         if line_subtotal > 0:
#                             # Calculate this line's proportion of the total
#                             line_proportion = line_subtotal / total_before_discount
#
#                             # Calculate discount amount for this line
#                             line_discount_amount = self.global_discount_fixed * line_proportion
#
#                             # Convert to percentage
#                             if line.price_unit > 0:
#                                 discount_pct = (line_discount_amount / (line.quantity * line.price_unit)) * 100
#                                 line.discount = min(discount_pct, 100)  # Cap at 100%
#         else:
#             # Clear discounts if global discount is removed
#             for line in self.invoice_line_ids:
#                 if not line.display_type:
#                     line.discount = 0.0
#
#     def _inverse_amount_total(self):
#         """Override to handle discount when setting amount_total directly."""
#         for move in self:
#             if move.global_discount_fixed:
#                 # If there's a global discount, we need to handle this differently
#                 # Just call parent for now
#                 super(AccountMove, move)._inverse_amount_total()
#             else:
#                 super(AccountMove, move)._inverse_amount_total()
#
#     @api.model_create_multi
#     def create(self, vals_list):
#         """Override create to apply discount to lines on creation."""
#         moves = super().create(vals_list)
#
#         for move in moves:
#             if move.is_invoice() and move.global_discount_fixed and move.global_discount_fixed > 0:
#                 _logger.info(f"=== INVOICE CREATED with discount: {move.global_discount_fixed} ===")
#
#                 # Apply discount to lines
#                 if move.invoice_line_ids:
#                     total_before_discount = sum(
#                         line.quantity * line.price_unit
#                         for line in move.invoice_line_ids
#                         if not line.display_type
#                     )
#
#                     if total_before_discount > 0:
#                         for line in move.invoice_line_ids:
#                             if not line.display_type:
#                                 line_subtotal = line.quantity * line.price_unit
#                                 if line_subtotal > 0:
#                                     line_proportion = line_subtotal / total_before_discount
#                                     line_discount_amount = move.global_discount_fixed * line_proportion
#
#                                     if line.price_unit > 0:
#                                         discount_pct = (line_discount_amount / (line.quantity * line.price_unit)) * 100
#                                         line.discount = min(discount_pct, 100)
#
#                         # Recompute the move to update all amounts
#                         move._recompute_dynamic_lines(recompute_all_taxes=True)
#
#         return moves
#
#     def write(self, vals):
#         """Override write to recompute when discount changes."""
#         # Handle discount change
#         if 'global_discount_fixed' in vals:
#             for move in self:
#                 if move.is_invoice() and vals['global_discount_fixed'] != move.global_discount_fixed:
#                     _logger.info(
#                         f"=== INVOICE DISCOUNT CHANGED from {move.global_discount_fixed} to {vals['global_discount_fixed']} ===")
#
#         res = super().write(vals)
#
#         # After write, apply the discount if it changed
#         if 'global_discount_fixed' in vals:
#             for move in self:
#                 if move.is_invoice() and move.state == 'draft':
#                     move._onchange_global_discount_fixed()
#                     move._recompute_dynamic_lines(recompute_all_taxes=True)
#
#         return res


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

    @api.depends(
        'line_ids.matched_debit_ids.debit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.matched_credit_ids.credit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.balance',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state',
        'line_ids.full_reconcile_id',
        'global_discount_fixed')
    def _compute_amount(self):
        """Override the main compute amount method to apply global discount."""
        for move in self:
            if move.is_invoice() and move.global_discount_fixed > 0:
                # Get the original computed values first
                total_untaxed = 0.0
                total_tax = 0.0

                for line in move.line_ids:
                    if line.display_type == 'product':
                        total_untaxed += line.price_subtotal
                        # Calculate tax for this line
                        if line.tax_ids:
                            taxes = line.tax_ids.compute_all(
                                line.price_unit,
                                line.currency_id,
                                line.quantity,
                                line.product_id,
                                move.partner_id
                            )
                            total_tax += sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))

                _logger.info(f"Invoice {move.name} - Original - Untaxed: {total_untaxed}, Tax: {total_tax}")

                # Apply discount to untaxed amount
                amount_untaxed_after_discount = total_untaxed - move.global_discount_fixed

                # Recalculate tax proportionally
                if total_untaxed > 0:
                    discount_ratio = amount_untaxed_after_discount / total_untaxed
                    total_tax = total_tax * discount_ratio

                _logger.info(f"After Discount - Untaxed: {amount_untaxed_after_discount}, Tax: {total_tax}")

                # Set the amounts
                move.amount_untaxed = amount_untaxed_after_discount
                move.amount_tax = total_tax
                move.amount_total = amount_untaxed_after_discount + total_tax
                move.amount_residual = amount_untaxed_after_discount + total_tax
            else:
                # Use standard Odoo computation
                super(AccountMove, move)._compute_amount()

    @api.onchange('global_discount_fixed', 'invoice_line_ids')
    def _onchange_global_discount_fixed(self):
        """Apply discount proportionally to invoice lines."""
        if not self.is_invoice() or not self.invoice_line_ids:
            return

        if self.global_discount_fixed and self.global_discount_fixed > 0:
            # Calculate total before discount (without any existing line discounts)
            total_before_discount = 0.0
            for line in self.invoice_line_ids:
                if not line.display_type:
                    # Calculate original price without discount
                    total_before_discount += line.quantity * line.price_unit

            if total_before_discount > 0:
                # Distribute discount proportionally to each line
                for line in self.invoice_line_ids:
                    if not line.display_type:
                        line_subtotal = line.quantity * line.price_unit
                        if line_subtotal > 0:
                            # Calculate this line's proportion of the total
                            line_proportion = line_subtotal / total_before_discount

                            # Calculate discount amount for this line
                            line_discount_amount = self.global_discount_fixed * line_proportion

                            # Convert to percentage
                            if line.price_unit > 0:
                                discount_pct = (line_discount_amount / (line.quantity * line.price_unit)) * 100
                                line.discount = min(discount_pct, 100)  # Cap at 100%
        else:
            # Clear discounts if global discount is removed
            for line in self.invoice_line_ids:
                if not line.display_type:
                    line.discount = 0.0

    def _inverse_amount_total(self):
        """Override to handle discount when setting amount_total directly."""
        for move in self:
            if move.global_discount_fixed:
                # If there's a global discount, we need to handle this differently
                # Just call parent for now
                super(AccountMove, move)._inverse_amount_total()
            else:
                super(AccountMove, move)._inverse_amount_total()

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to apply discount to lines on creation."""
        moves = super().create(vals_list)

        for move in moves:
            if move.is_invoice() and move.global_discount_fixed and move.global_discount_fixed > 0:
                _logger.info(f"=== INVOICE CREATED with discount: {move.global_discount_fixed} ===")

                # Apply discount to lines
                if move.invoice_line_ids:
                    total_before_discount = sum(
                        line.quantity * line.price_unit
                        for line in move.invoice_line_ids
                        if not line.display_type
                    )

                    if total_before_discount > 0:
                        for line in move.invoice_line_ids:
                            if not line.display_type:
                                line_subtotal = line.quantity * line.price_unit
                                if line_subtotal > 0:
                                    line_proportion = line_subtotal / total_before_discount
                                    line_discount_amount = move.global_discount_fixed * line_proportion

                                    if line.price_unit > 0:
                                        discount_pct = (line_discount_amount / (line.quantity * line.price_unit)) * 100
                                        line.discount = min(discount_pct, 100)

                        # Recompute the move to update all amounts
                        move._recompute_dynamic_lines(recompute_all_taxes=True)

        return moves

    def write(self, vals):
        """Override write to recompute when discount changes."""
        # Handle discount change
        if 'global_discount_fixed' in vals:
            for move in self:
                if move.is_invoice() and vals.get('global_discount_fixed', 0) != move.global_discount_fixed:
                    _logger.info(
                        f"=== INVOICE DISCOUNT CHANGED from {move.global_discount_fixed} to {vals['global_discount_fixed']} ===")

        res = super().write(vals)

        # After write, apply the discount if it changed
        if 'global_discount_fixed' in vals:
            for move in self:
                if move.is_invoice() and move.state == 'draft':
                    move._onchange_global_discount_fixed()
                    move._recompute_dynamic_lines(recompute_all_taxes=True)

        return res
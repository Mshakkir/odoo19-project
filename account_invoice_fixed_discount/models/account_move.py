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
# currently successfully used code


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
#     @api.depends('invoice_line_ids.price_subtotal', 'invoice_line_ids.discount', 'global_discount_fixed')
#     def _compute_amounts_with_discount(self):
#         """Calculate amounts before and after global discount."""
#         for move in self:
#             if move.is_invoice():
#                 # Calculate the ORIGINAL amount before any discounts
#                 amount_undiscounted = 0.0
#                 for line in move.invoice_line_ids:
#                     if not line.display_type:
#                         # Calculate original amount WITHOUT discount
#                         original_line_amount = line.quantity * line.price_unit
#                         amount_undiscounted += original_line_amount
#
#                 move.amount_undiscounted = amount_undiscounted
#                 move.amount_after_discount = amount_undiscounted - move.global_discount_fixed
#
#                 _logger.info(f"=== COMPUTE DISCOUNT AMOUNTS ===")
#                 _logger.info(
#                     f"Undiscounted: {amount_undiscounted}, Discount: {move.global_discount_fixed}, After: {move.amount_after_discount}")
#             else:
#                 move.amount_undiscounted = 0.0
#                 move.amount_after_discount = 0.0
#
#     @api.onchange('global_discount_fixed')
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
#     @api.model_create_multi
#     def create(self, vals_list):
#         """Override create to apply discount to lines on creation."""
#         moves = super().create(vals_list)
#
#         for move in moves:
#             if move.is_invoice() and move.global_discount_fixed and move.global_discount_fixed > 0:
#                 _logger.info(f"=== INVOICE CREATED with discount: {move.global_discount_fixed} ===")
#
#                 # Check if lines already have discounts (coming from sale order)
#                 has_existing_discounts = any(
#                     line.discount > 0
#                     for line in move.invoice_line_ids
#                     if not line.display_type
#                 )
#
#                 if has_existing_discounts:
#                     _logger.info("Lines already have discounts from sale order - skipping distribution")
#                     # Lines already have the discount applied from sale order
#                     # Just recompute the display fields
#                     move._compute_amounts_with_discount()
#                 else:
#                     _logger.info("No existing discounts - applying global discount to lines")
#                     # Apply discount to lines
#                     if move.invoice_line_ids:
#                         total_before_discount = sum(
#                             line.quantity * line.price_unit
#                             for line in move.invoice_line_ids
#                             if not line.display_type
#                         )
#
#                         if total_before_discount > 0:
#                             for line in move.invoice_line_ids:
#                                 if not line.display_type:
#                                     line_subtotal = line.quantity * line.price_unit
#                                     if line_subtotal > 0:
#                                         line_proportion = line_subtotal / total_before_discount
#                                         line_discount_amount = move.global_discount_fixed * line_proportion
#
#                                         if line.price_unit > 0:
#                                             discount_pct = (line_discount_amount / (
#                                                         line.quantity * line.price_unit)) * 100
#                                             line.discount = min(discount_pct, 100)
#
#                             # Recompute the move to update all amounts
#                             move._recompute_dynamic_lines(recompute_all_taxes=True)
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
#                     # Check if we need to redistribute
#                     if vals['global_discount_fixed'] > 0:
#                         move._onchange_global_discount_fixed()
#                         move._recompute_dynamic_lines(recompute_all_taxes=True)
#                     else:
#                         # Clear all line discounts
#                         for line in move.invoice_line_ids:
#                             if not line.display_type:
#                                 line.discount = 0.0
#                         move._recompute_dynamic_lines(recompute_all_taxes=True)
#
#         return res


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

    # amount_undiscounted = fields.Monetary(
    #     string='Amount Undiscounted',
    #     compute='_compute_amounts_with_discount',
    #     store=True,
    #     currency_field='currency_id'
    # )
    #
    # amount_after_discount = fields.Monetary(
    #     string='Amount After Discount',
    #     compute='_compute_amounts_with_discount',
    #     store=True,
    #     currency_field='currency_id'
    # )
    #
    # @api.depends('invoice_line_ids.quantity', 'invoice_line_ids.price_unit', 'invoice_line_ids.price_subtotal',
    #              'global_discount_fixed')
    # def _compute_amounts_with_discount(self):
    #     """Calculate amounts before and after global discount for display."""
    #     for move in self:
    #         if move.is_invoice():
    #             # Calculate ORIGINAL amount WITHOUT any discounts
    #             amount_undiscounted = sum(
    #                 line.quantity * line.price_unit
    #                 for line in move.invoice_line_ids
    #                 if not line.display_type
    #             )
    #             # Calculate amount after line discounts but before global discount
    #             amount_with_line_discounts = sum(
    #                 line.price_subtotal
    #                 for line in move.invoice_line_ids
    #                 if not line.display_type
    #             )
    #
    #             move.amount_undiscounted = amount_undiscounted
    #             # After discount should be the actual subtotal (which already has discounts applied)
    #             move.amount_after_discount = amount_with_line_discounts
    #
    #             _logger.info(
    #                 f"Amounts - Original: {amount_undiscounted}, After line discounts: {amount_with_line_discounts}, Global discount: {move.global_discount_fixed}")
    #         else:
    #             move.amount_undiscounted = 0.0
    #             move.amount_after_discount = 0.0
    #
    # @api.onchange('global_discount_fixed')
    # def _onchange_global_discount_fixed(self):
    #     """Apply discount proportionally to invoice lines."""
    #     if not self.is_invoice() or not self.invoice_line_ids:
    #         return
    #
    #     if self.global_discount_fixed and self.global_discount_fixed > 0:
    #         total_before_discount = sum(
    #             line.quantity * line.price_unit
    #             for line in self.invoice_line_ids
    #             if not line.display_type
    #         )
    #
    #         if total_before_discount > 0:
    #             for line in self.invoice_line_ids:
    #                 if not line.display_type:
    #                     line_subtotal = line.quantity * line.price_unit
    #                     if line_subtotal > 0:
    #                         line_proportion = line_subtotal / total_before_discount
    #                         line_discount_amount = self.global_discount_fixed * line_proportion
    #
    #                         if line.price_unit > 0:
    #                             discount_pct = (line_discount_amount / (line.quantity * line.price_unit)) * 100
    #                             line.discount = min(discount_pct, 100)
    #     else:
    #         for line in self.invoice_line_ids:
    #             if not line.display_type:
    #                 line.discount = 0.0
    #
    # @api.model_create_multi
    # def create(self, vals_list):
    #     """Override create to apply discount to lines on creation."""
    #     moves = super().create(vals_list)
    #
    #     for move in moves:
    #         if move.is_invoice() and move.global_discount_fixed and move.global_discount_fixed > 0:
    #             _logger.info(f"=== INVOICE CREATED with discount: {move.global_discount_fixed} ===")
    #
    #             has_existing_discounts = any(
    #                 line.discount > 0
    #                 for line in move.invoice_line_ids
    #                 if not line.display_type
    #             )
    #
    #             if has_existing_discounts:
    #                 _logger.info("Lines already have discounts from sale order")
    #             else:
    #                 _logger.info("Applying global discount to lines")
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
    #                                         discount_pct = (line_discount_amount / (
    #                                                     line.quantity * line.price_unit)) * 100
    #                                         line.discount = min(discount_pct, 100)
    #
    #                         move._recompute_dynamic_lines(recompute_all_taxes=True)
    #
    #     return moves
    #
    # def write(self, vals):
    #     """Override write to recompute when discount changes."""
    #     if 'global_discount_fixed' in vals:
    #         for move in self:
    #             if move.is_invoice() and vals['global_discount_fixed'] != move.global_discount_fixed:
    #                 _logger.info(
    #                     f"=== DISCOUNT CHANGED from {move.global_discount_fixed} to {vals['global_discount_fixed']} ===")
    #
    #     res = super().write(vals)
    #
    #     if 'global_discount_fixed' in vals:
    #         for move in self:
    #             if move.is_invoice() and move.state == 'draft':
    #                 if vals['global_discount_fixed'] > 0:
    #                     move._onchange_global_discount_fixed()
    #                     move._recompute_dynamic_lines(recompute_all_taxes=True)
    #                 else:
    #                     for line in move.invoice_line_ids:
    #                         if not line.display_type:
    #                             line.discount = 0.0
    #                     move._recompute_dynamic_lines(recompute_all_taxes=True)
    #
    #     return res


# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
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

    @api.depends('invoice_line_ids.price_subtotal', 'invoice_line_ids.discount', 'global_discount_fixed')
    def _compute_amounts_with_discount(self):
        """Calculate amounts before and after global discount."""
        for move in self:
            if move.is_invoice():
                # Calculate the ORIGINAL amount before any discounts
                amount_undiscounted = 0.0
                for line in move.invoice_line_ids:
                    if not line.display_type:
                        # Calculate original amount WITHOUT line-level discount
                        original_line_amount = line.quantity * line.price_unit
                        amount_undiscounted += original_line_amount

                move.amount_undiscounted = amount_undiscounted
                move.amount_after_discount = amount_undiscounted - (move.global_discount_fixed or 0.0)
            else:
                move.amount_undiscounted = 0.0
                move.amount_after_discount = 0.0

    def _recompute_dynamic_lines(self, recompute_all_taxes=False, recompute_tax_base_amount=False):
        """
        Override to apply global discount to invoice lines and journal entries.
        This ensures the journal entry remains balanced.
        """
        # Call super to let Odoo compute standard amounts and journal lines
        res = super()._recompute_dynamic_lines(
            recompute_all_taxes=recompute_all_taxes,
            recompute_tax_base_amount=recompute_tax_base_amount
        )

        for move in self:
            # Only process invoices/bills with discount
            if not move.is_invoice():
                continue

            if not move.global_discount_fixed or move.global_discount_fixed <= 0:
                continue

            # Create or update discount line
            self._apply_global_discount(move)

        return res

    def _apply_global_discount(self, move):
        """Apply global discount by creating a discount line."""
        discount_account = self._get_discount_account(move)

        if not discount_account:
            _logger.warning(f"No discount account configured for invoice {move.name}")
            return

        # Find existing discount line
        discount_line = move.line_ids.filtered(
            lambda l: l.account_id == discount_account and l.exclude_from_invoice_tab
        )

        # Determine the sign based on move type
        # For customer invoices: discount reduces receivable (credit)
        # For vendor bills: discount reduces payable (debit)
        sign = 1 if move.move_type in ('out_invoice', 'out_refund') else -1
        discount_amount = move.global_discount_fixed * sign

        if discount_line:
            # Update existing line
            discount_line.with_context(check_move_validity=False).write({
                'debit': discount_amount if discount_amount > 0 else 0.0,
                'credit': -discount_amount if discount_amount < 0 else 0.0,
                'amount_currency': discount_amount if move.currency_id != move.company_currency_id else 0.0,
            })
        else:
            # Create new discount line
            line_vals = {
                'move_id': move.id,
                'account_id': discount_account.id,
                'name': f'Global Discount: {move.global_discount_fixed}',
                'debit': discount_amount if discount_amount > 0 else 0.0,
                'credit': -discount_amount if discount_amount < 0 else 0.0,
                'amount_currency': discount_amount if move.currency_id != move.company_currency_id else 0.0,
                'currency_id': move.currency_id.id if move.currency_id != move.company_currency_id else False,
                'exclude_from_invoice_tab': True,
                'partner_id': move.partner_id.id,
            }

            move.with_context(check_move_validity=False).write({
                'line_ids': [(0, 0, line_vals)]
            })

        # Recompute totals
        move._compute_amount()

    def _get_discount_account(self, move):
        """Get the appropriate discount account based on invoice type."""
        # Get from company settings or use expense/income account
        company = move.company_id

        if move.move_type in ('out_invoice', 'out_refund'):
            # Sales discount - use sales discount account or fallback
            # You can add a field to res.company for this
            account = self.env['account.account'].search([
                ('company_id', '=', company.id),
                ('code', '=like', '4090%'),  # Typical sales discount account
            ], limit=1)

            if not account:
                # Fallback to generic expense account
                account = self.env['account.account'].search([
                    ('company_id', '=', company.id),
                    ('account_type', '=', 'expense'),
                ], limit=1)
        else:
            # Purchase discount - use purchase discount account
            account = self.env['account.account'].search([
                ('company_id', '=', company.id),
                ('code', '=like', '7090%'),  # Typical purchase discount account
            ], limit=1)

            if not account:
                # Fallback to generic income account
                account = self.env['account.account'].search([
                    ('company_id', '=', company.id),
                    ('account_type', '=', 'income'),
                ], limit=1)

        return account

    @api.model_create_multi
    def create(self, vals_list):
        """Apply discount when creating invoice."""
        moves = super().create(vals_list)

        for move in moves:
            if move.is_invoice() and move.global_discount_fixed and move.global_discount_fixed > 0:
                _logger.info(f"Invoice created with discount: {move.global_discount_fixed}")
                # Force recomputation
                move._recompute_dynamic_lines()

        return moves

    def write(self, vals):
        """Recompute when discount changes."""
        res = super().write(vals)

        if 'global_discount_fixed' in vals:
            for move in self:
                if move.is_invoice():
                    _logger.info(f"Invoice discount changed to: {move.global_discount_fixed}")
                    move._recompute_dynamic_lines()

        return res

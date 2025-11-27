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

    @api.depends('line_ids.balance', 'line_ids.amount_currency', 'global_discount_fixed')
    def _compute_amount(self):
        """Override to apply global discount."""
        # Call super first
        super()._compute_amount()

        # Then apply discount by modifying amounts
        for move in self:
            if not move.is_invoice():
                continue

            if not move.global_discount_fixed or move.global_discount_fixed <= 0:
                continue

            # Simply reduce the amounts by discount
            discount = move.global_discount_fixed

            # Get the amounts before discount
            original_untaxed = sum(move.invoice_line_ids.filtered(
                lambda l: not l.display_type
            ).mapped('price_subtotal'))

            original_tax = sum(move.line_ids.filtered(
                lambda l: l.tax_line_id
            ).mapped('balance')) * (-1 if move.move_type in ('out_invoice', 'out_refund') else 1)

            # Apply discount proportionally
            if original_untaxed > 0:
                discount_ratio = max(0, (original_untaxed - discount) / original_untaxed)
                new_untaxed = original_untaxed - discount
                new_tax = original_tax * discount_ratio
            else:
                new_untaxed = 0
                new_tax = 0

            new_total = new_untaxed + new_tax

            # Update the move amounts
            move.amount_untaxed = new_untaxed
            move.amount_tax = new_tax
            move.amount_total = new_total
            move.amount_residual = new_total - move.amount_paid

            # Update signed amounts
            sign = -1 if move.move_type in ('in_invoice', 'out_refund') else 1
            move.amount_untaxed_signed = new_untaxed * sign
            move.amount_total_signed = new_total * sign
            move.amount_residual_signed = move.amount_residual * sign
            move.amount_total_in_currency_signed = new_total * sign

            _logger.info(f"Applied discount of {discount} to {move.name}. New total: {new_total}")

    def _sync_dynamic_lines(self, container):
        """Override to add discount line to journal entries."""
        # Call parent to sync invoice lines to journal entries
        res = super()._sync_dynamic_lines(container)

        # Add discount line if needed
        for move in container['records']:
            if move.global_discount_fixed and move.global_discount_fixed > 0:
                move._add_discount_line_to_journal(container)

        return res

    def _add_discount_line_to_journal(self, container):
        """Add the discount line to journal entries."""
        self.ensure_one()

        discount_account = self._get_discount_account()
        if not discount_account:
            return

        # Find if discount line already exists
        existing_discount = None
        for line_data in container.get('to_write', []):
            if 'name' in line_data[1] and 'Global Discount:' in str(line_data[1].get('name', '')):
                existing_discount = line_data
                break

        # Calculate the discount line values
        if self.move_type in ('out_invoice', 'in_refund'):
            debit = self.global_discount_fixed
            credit = 0.0
        else:
            debit = 0.0
            credit = self.global_discount_fixed

        line_vals = {
            'name': f'Global Discount: {self.global_discount_fixed}',
            'debit': debit,
            'credit': credit,
            'amount_currency': debit - credit,
            'account_id': discount_account.id,
            'move_id': self.id,
            'partner_id': self.partner_id.id,
            'display_type': 'payment_term',
        }

        if existing_discount:
            existing_discount[1].update(line_vals)
        else:
            container.setdefault('to_create', []).append(line_vals)

    def _get_discount_account(self):
        """Get the appropriate discount account based on invoice type."""
        company = self.company_id

        # Try to get from company settings first
        if self.move_type in ('out_invoice', 'out_refund'):
            if hasattr(company, 'sales_discount_account_id') and company.sales_discount_account_id:
                return company.sales_discount_account_id

            account = self.env['account.account'].search([
                ('code', '=like', '409%'),
            ], limit=1)

            if not account:
                account = self.env['account.account'].search([
                    ('account_type', '=', 'expense'),
                ], limit=1)
        else:
            if hasattr(company, 'purchase_discount_account_id') and company.purchase_discount_account_id:
                return company.purchase_discount_account_id

            account = self.env['account.account'].search([
                ('code', '=like', '709%'),
            ], limit=1)

            if not account:
                account = self.env['account.account'].search([
                    ('account_type', '=', 'income_other'),
                ], limit=1)

        return account

    @api.model_create_multi
    def create(self, vals_list):
        """Apply discount when creating invoice."""
        moves = super().create(vals_list)

        for move in moves:
            if move.is_invoice() and move.global_discount_fixed and move.global_discount_fixed > 0:
                _logger.info(f"Invoice created with discount: {move.global_discount_fixed}")
                # Trigger recomputation
                move.invalidate_recordset(['amount_total', 'amount_untaxed', 'amount_tax'])

        return moves

    def write(self, vals):
        """Recompute when discount changes."""
        res = super().write(vals)

        if 'global_discount_fixed' in vals:
            for move in self:
                if move.is_invoice():
                    _logger.info(f"Invoice discount changed to: {move.global_discount_fixed}")
                    # Trigger recomputation
                    move.invalidate_recordset(['amount_total', 'amount_untaxed', 'amount_tax'])

        return res

    def _inverse_amount_total(self):
        """Override to prevent issues when amount_total is set directly."""
        for move in self:
            if not move.global_discount_fixed or move.global_discount_fixed <= 0:
                super(AccountMove, move)._inverse_amount_total()
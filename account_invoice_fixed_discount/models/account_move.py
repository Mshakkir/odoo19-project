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
#                 # Calculate amount without ANY discount (original price_unit * quantity)
#                 amount_undiscounted = 0.0
#                 amount_with_line_discount = 0.0
#
#                 for line in move.invoice_line_ids:
#                     if not line.display_type:
#                         # Original amount without any discount
#                         line_total = line.quantity * line.price_unit
#                         amount_undiscounted += line_total
#
#                         # Amount after line discount (this is price_subtotal)
#                         amount_with_line_discount += line.price_subtotal
#
#                 move.amount_undiscounted = amount_undiscounted
#
#                 # If there's a global discount, amount_after_discount shows the line total after discount
#                 # Otherwise it shows the same as undiscounted
#                 if move.global_discount_fixed > 0:
#                     move.amount_after_discount = amount_undiscounted - move.global_discount_fixed
#                 else:
#                     move.amount_after_discount = amount_with_line_discount
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
#     @api.model_create_multi
#     def create(self, vals_list):
#         """Override create to apply discount to lines BEFORE creation."""
#
#         # First, process the discount in vals_list BEFORE calling super
#         for vals in vals_list:
#             if vals.get('move_type') in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund'):
#                 global_discount = vals.get('global_discount_fixed', 0.0)
#
#                 if global_discount and global_discount > 0 and vals.get('invoice_line_ids'):
#                     _logger.info(f"=== APPLYING DISCOUNT BEFORE CREATE: {global_discount} ===")
#
#                     # Calculate total before discount from invoice_line_ids commands
#                     total_before_discount = 0.0
#                     line_commands = vals['invoice_line_ids']
#
#                     for command in line_commands:
#                         # command format: (0, 0, {values}) for create
#                         if command[0] == 0 and command[2]:
#                             line_vals = command[2]
#                             if not line_vals.get('display_type'):
#                                 quantity = line_vals.get('quantity', 0)
#                                 price_unit = line_vals.get('price_unit', 0)
#                                 total_before_discount += quantity * price_unit
#
#                     if total_before_discount > 0:
#                         # Apply discount to each line
#                         for command in line_commands:
#                             if command[0] == 0 and command[2]:
#                                 line_vals = command[2]
#                                 if not line_vals.get('display_type'):
#                                     quantity = line_vals.get('quantity', 0)
#                                     price_unit = line_vals.get('price_unit', 0)
#                                     line_subtotal = quantity * price_unit
#
#                                     if line_subtotal > 0:
#                                         line_proportion = line_subtotal / total_before_discount
#                                         line_discount_amount = global_discount * line_proportion
#
#                                         if price_unit > 0:
#                                             discount_pct = (line_discount_amount / (quantity * price_unit)) * 100
#                                             line_vals['discount'] = min(discount_pct, 100)
#                                             _logger.info(f"Applied {discount_pct:.2f}% discount to line")
#
#         # Now create the moves with discounts already in place
#         moves = super().create(vals_list)
#
#         return moves
#
#     def write(self, vals):
#         """Override write to recompute when discount changes."""
#         # Handle discount change
#         if 'global_discount_fixed' in vals:
#             for move in self:
#                 if move.is_invoice() and vals.get('global_discount_fixed', 0) != move.global_discount_fixed:
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
from odoo.tools import float_is_zero
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

    @api.depends('invoice_line_ids.price_subtotal', 'invoice_line_ids.discount', 'invoice_line_ids.price_total',
                 'global_discount_fixed')
    def _compute_amounts_with_discount(self):
        """Calculate amounts before and after global discount."""
        for move in self:
            if move.is_invoice():
                # Calculate amount without ANY discount (original price_unit * quantity)
                amount_undiscounted = 0.0

                for line in move.invoice_line_ids:
                    if not line.display_type:
                        # Original amount without any discount
                        amount_undiscounted += line.quantity * line.price_unit

                move.amount_undiscounted = amount_undiscounted
                move.amount_after_discount = amount_undiscounted - move.global_discount_fixed

                _logger.info(
                    f"Invoice - Undiscounted: {amount_undiscounted}, Discount: {move.global_discount_fixed}, After: {move.amount_after_discount}")
            else:
                move.amount_undiscounted = 0.0
                move.amount_after_discount = 0.0

    @api.depends('invoice_line_ids.price_subtotal', 'global_discount_fixed',
                 'line_ids.amount_currency', 'line_ids.currency_id', 'line_ids.debit',
                 'line_ids.credit', 'line_ids.balance', 'currency_id', 'partner_id')
    def _compute_amount(self):
        """Override to adjust totals based on discount."""
        # Call parent first to compute everything normally
        super()._compute_amount()

        # Then adjust only if there's a discount
        for move in self:
            if move.is_invoice() and move.global_discount_fixed > 0:
                _logger.info(f"=== Adjusting amounts for invoice with discount {move.global_discount_fixed} ===")
                _logger.info(
                    f"Before adjustment - Untaxed: {move.amount_untaxed}, Tax: {move.amount_tax}, Total: {move.amount_total}")

                # The discount was already applied to lines, so amounts should be correct
                # Just log for debugging
                total_from_lines = sum(
                    line.price_subtotal
                    for line in move.invoice_line_ids
                    if not line.display_type
                )
                _logger.info(f"Total from lines: {total_from_lines}")
                _logger.info(
                    f"After adjustment - Untaxed: {move.amount_untaxed}, Tax: {move.amount_tax}, Total: {move.amount_total}")

    @api.onchange('global_discount_fixed')
    def _onchange_global_discount_fixed(self):
        """Apply discount proportionally to invoice lines when changed manually."""
        if not self.is_invoice() or not self.invoice_line_ids:
            return

        _logger.info(f"=== ONCHANGE DISCOUNT: {self.global_discount_fixed} ===")

        if self.global_discount_fixed and self.global_discount_fixed > 0:
            # Calculate total before discount
            total_before_discount = sum(
                line.quantity * line.price_unit
                for line in self.invoice_line_ids
                if not line.display_type
            )

            if total_before_discount > 0:
                # Distribute discount proportionally to each line
                for line in self.invoice_line_ids:
                    if not line.display_type:
                        line_subtotal = line.quantity * line.price_unit
                        if line_subtotal > 0 and line.price_unit > 0:
                            line_proportion = line_subtotal / total_before_discount
                            line_discount_amount = self.global_discount_fixed * line_proportion
                            discount_pct = (line_discount_amount / (line.quantity * line.price_unit)) * 100
                            line.discount = min(discount_pct, 100)
                            _logger.info(f"Line discount set to: {line.discount}%")
        else:
            # Clear discounts if global discount is removed
            for line in self.invoice_line_ids:
                if not line.display_type:
                    line.discount = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to apply discount to lines on creation."""

        # Apply discount to vals_list BEFORE creating
        for vals in vals_list:
            move_type = vals.get('move_type', '')
            if move_type in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund'):
                global_discount = vals.get('global_discount_fixed', 0.0)

                if global_discount and global_discount > 0:
                    _logger.info(f"=== CREATE: Applying discount {global_discount} ===")

                    invoice_line_ids = vals.get('invoice_line_ids', [])
                    if invoice_line_ids:
                        # Calculate total
                        total_before_discount = 0.0
                        for cmd in invoice_line_ids:
                            if cmd[0] in (0, 1) and len(cmd) > 2 and isinstance(cmd[2], dict):
                                line_vals = cmd[2]
                                if not line_vals.get('display_type'):
                                    qty = line_vals.get('quantity', 1)
                                    price = line_vals.get('price_unit', 0)
                                    total_before_discount += qty * price

                        _logger.info(f"Total before discount: {total_before_discount}")

                        if total_before_discount > 0:
                            # Apply proportional discount to each line
                            for cmd in invoice_line_ids:
                                if cmd[0] in (0, 1) and len(cmd) > 2 and isinstance(cmd[2], dict):
                                    line_vals = cmd[2]
                                    if not line_vals.get('display_type'):
                                        qty = line_vals.get('quantity', 1)
                                        price = line_vals.get('price_unit', 0)
                                        line_total = qty * price

                                        if line_total > 0 and price > 0:
                                            proportion = line_total / total_before_discount
                                            line_discount_amt = global_discount * proportion
                                            discount_pct = (line_discount_amt / line_total) * 100
                                            line_vals['discount'] = min(discount_pct, 100)
                                            _logger.info(f"Setting line discount to {discount_pct:.2f}%")

        moves = super().create(vals_list)
        return moves

    def write(self, vals):
        """Override write to recompute when discount changes."""
        if 'global_discount_fixed' in vals:
            for move in self:
                if move.is_invoice():
                    _logger.info(
                        f"=== WRITE: Discount changing from {move.global_discount_fixed} to {vals['global_discount_fixed']} ===")

        res = super().write(vals)

        # After write, apply the discount if it changed and invoice is still draft
        if 'global_discount_fixed' in vals:
            for move in self:
                if move.is_invoice() and move.state == 'draft':
                    _logger.info("Triggering onchange after write")
                    move._onchange_global_discount_fixed()
                    # Force recomputation
                    move.with_context(check_move_validity=False)._recompute_dynamic_lines(recompute_all_taxes=True)

        return res
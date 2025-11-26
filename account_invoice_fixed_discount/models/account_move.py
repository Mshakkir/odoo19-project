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

from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    global_discount_fixed = fields.Monetary(
        string="Global Discount (Fixed)",
        default=0.0,
        currency_field="currency_id",
        help="Apply a fixed discount to the entire invoice. This will be shown as a separate line in totals.",
        tracking=True,
        readonly=False,  # We handle readonly in the view based on state
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

    @api.depends('line_ids.price_subtotal', 'global_discount_fixed')
    def _compute_amounts_with_discount(self):
        """Calculate amounts before and after global discount."""
        for move in self:
            # Only for invoices and credit notes
            if move.is_invoice():
                invoice_lines = move.line_ids.filtered(
                    lambda line: line.display_type == 'product'
                )
                amount_undiscounted = sum(invoice_lines.mapped('price_subtotal'))
                move.amount_undiscounted = amount_undiscounted
                move.amount_after_discount = amount_undiscounted - move.global_discount_fixed
            else:
                move.amount_undiscounted = 0.0
                move.amount_after_discount = 0.0

    @api.depends(
        'line_ids.price_subtotal',
        'line_ids.tax_base_amount',
        'line_ids.tax_line_id',
        'line_ids.price_total',
        'partner_id',
        'currency_id',
        'global_discount_fixed'
    )
    def _compute_amount(self):
        """Override to apply global discount and recalculate taxes."""
        for move in self:
            if move.is_invoice():
                # Get invoice lines (excluding tax lines and display lines)
                invoice_lines = move.line_ids.filtered(
                    lambda line: line.display_type == 'product'
                )

                # Get tax lines
                tax_lines = move.line_ids.filtered(
                    lambda line: line.display_type == 'tax'
                )

                # Calculate original amounts
                amount_untaxed = sum(invoice_lines.mapped('price_subtotal'))
                amount_tax = sum(tax_lines.mapped('price_subtotal'))

                _logger.info(f"=== INVOICE COMPUTE ===")
                _logger.info(f"Original - Untaxed: {amount_untaxed}, Tax: {amount_tax}")

                # Apply global discount
                if move.global_discount_fixed and move.global_discount_fixed > 0:
                    # Subtract discount from untaxed amount
                    amount_untaxed_after_discount = amount_untaxed - move.global_discount_fixed

                    # Recalculate tax proportionally
                    if amount_untaxed > 0:
                        discount_ratio = amount_untaxed_after_discount / amount_untaxed
                        amount_tax = amount_tax * discount_ratio

                    _logger.info(f"After Discount - Untaxed: {amount_untaxed_after_discount}, Tax: {amount_tax}")

                    # Calculate total
                    sign = move.direction_sign
                    move.amount_untaxed = amount_untaxed_after_discount * sign
                    move.amount_tax = amount_tax * sign
                    move.amount_total = move.amount_untaxed + move.amount_tax
                    move.amount_residual = move.amount_total - move.amount_paid
                    move.amount_untaxed_signed = amount_untaxed_after_discount * (
                        -1 if move.move_type in ['in_invoice', 'out_refund'] else 1)
                    move.amount_total_signed = move.amount_total * (
                        -1 if move.move_type in ['in_invoice', 'out_refund'] else 1)
                else:
                    # No discount, use parent computation
                    super(AccountMove, move)._compute_amount()
            else:
                # Not an invoice, use parent computation
                super(AccountMove, move)._compute_amount()
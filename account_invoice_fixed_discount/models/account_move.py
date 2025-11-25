# # Copyright 2017 ForgeFlow S.L.
# # License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)
#
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
#
#
#
#


# Copyright 2017 ForgeFlow S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

from odoo import api, fields, models
from odoo.tools.float_utils import float_is_zero


class AccountMove(models.Model):
    _inherit = "account.move"

    global_discount_fixed = fields.Monetary(
        string="Global Discount (Fixed)",
        default=0.0,
        currency_field="currency_id",
        help="Apply a fixed discount to the entire invoice. This will appear as a separate discount line.",
        tracking=True,
        states={'posted': [('readonly', True)]},
    )

    @api.onchange('global_discount_fixed')
    def _onchange_global_discount_fixed(self):
        """Add or update a global discount line in the invoice."""
        # Find existing global discount line
        discount_line = self.invoice_line_ids.filtered(lambda l: l.is_global_discount_line)

        currency = self.currency_id or self.company_id.currency_id

        if float_is_zero(self.global_discount_fixed, precision_rounding=currency.rounding):
            # Remove discount line if discount is zero
            if discount_line:
                self.invoice_line_ids = [(3, discount_line.id)]
            return

        # Get discount product
        discount_product = self.env.ref('account_invoice_fixed_discount.product_global_discount',
                                        raise_if_not_found=False)

        if not discount_product:
            return

        # Get income account
        account = discount_product.property_account_income_id or discount_product.categ_id.property_account_income_categ_id
        if not account:
            account = self.env['account.account'].search([
                ('account_type', '=', 'income'),
                ('company_id', '=', self.company_id.id)
            ], limit=1)

        discount_values = {
            'product_id': discount_product.id,
            'name': 'Global Discount',
            'quantity': 1,
            'price_unit': -self.global_discount_fixed,  # Negative amount for discount
            'account_id': account.id,
            'is_global_discount_line': True,
            'sequence': 9999,  # Put at the end
        }

        if discount_line:
            # Update existing line
            discount_line.write({
                'price_unit': -self.global_discount_fixed,
            })
        else:
            # Create new line
            self.invoice_line_ids = [(0, 0, discount_values)]


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    is_global_discount_line = fields.Boolean(
        string="Is Global Discount Line",
        default=False,
        help="Identifies this line as the global discount line"
    )
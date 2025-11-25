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
        help="Apply a fixed discount to the entire invoice. This will be distributed proportionally across all invoice lines.",
        tracking=True,
        states={'posted': [('readonly', True)]},
    )

    @api.onchange('global_discount_fixed')
    def _onchange_global_discount_fixed(self):
        """Distribute the global discount proportionally across all invoice lines."""
        if not self.invoice_line_ids:
            return

        currency = self.currency_id or self.company_id.currency_id

        if float_is_zero(self.global_discount_fixed, precision_rounding=currency.rounding):
            # Clear individual line discounts if global discount is removed
            for line in self.invoice_line_ids.filtered(lambda l: not l.display_type):
                if line.discount_fixed > 0:
                    line.discount_fixed = 0.0
            return

        # Calculate total before any discount (only for product lines)
        product_lines = self.invoice_line_ids.filtered(lambda l: not l.display_type)
        total_before_discount = sum(line.quantity * line.price_unit for line in product_lines)

        if float_is_zero(total_before_discount, precision_rounding=currency.rounding):
            return

        # Distribute global discount proportionally
        for line in product_lines:
            line_subtotal = line.quantity * line.price_unit
            if not float_is_zero(line_subtotal, precision_rounding=currency.rounding):
                # Calculate proportional discount for this line
                line_proportion = line_subtotal / total_before_discount
                line.discount_fixed = self.global_discount_fixed * line_proportion
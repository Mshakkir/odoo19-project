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
        help="Apply a fixed discount to the entire invoice. This will be added as a separate discount line.",
        tracking=True,
        states={'posted': [('readonly', True)]},
    )

    @api.onchange('global_discount_fixed')
    def _onchange_global_discount_fixed(self):
        """Add or update a discount line for the global discount."""
        if not self.invoice_line_ids:
            return

        currency = self.currency_id or self.company_id.currency_id

        # Find existing discount line
        discount_line = self.invoice_line_ids.filtered(
            lambda l: not l.display_type and l.product_id and
                      l.product_id.id == self._get_global_discount_product().id
        )

        if float_is_zero(self.global_discount_fixed, precision_rounding=currency.rounding):
            # Remove discount line if global discount is zero
            if discount_line:
                self.invoice_line_ids = [(2, discount_line.id, 0)]
            return

        # Get the discount product
        discount_product = self._get_global_discount_product()

        if discount_line:
            # Update existing line
            discount_line.write({
                'price_unit': -abs(self.global_discount_fixed),
                'quantity': 1.0,
            })
        else:
            # Create new discount line at the end
            # Get the last sequence number
            max_sequence = max([line.sequence for line in self.invoice_line_ids if line.sequence], default=10)

            self.invoice_line_ids = [(0, 0, {
                'product_id': discount_product.id,
                'name': 'Global Discount',
                'quantity': 1.0,
                'price_unit': -abs(self.global_discount_fixed),
                'tax_ids': [(6, 0, [])],  # No taxes on discount line
                'sequence': max_sequence + 10,  # Put it at the end
            })]

    def _get_global_discount_product(self):
        """Get or create a product for global discount lines."""
        discount_product = self.env.ref(
            'account_invoice_fixed_discount.product_global_discount',
            raise_if_not_found=False
        )

        if not discount_product:
            # Create the discount product if it doesn't exist
            discount_product = self.env['product.product'].create({
                'name': 'Global Discount',
                'type': 'service',
                'invoice_policy': 'order',
                'list_price': 0.0,
                'taxes_id': [(5, 0, 0)],  # No taxes
                'supplier_taxes_id': [(5, 0, 0)],
                'default_code': 'GLOBAL_DISCOUNT',
            })

            # Create external identifier for future reference
            self.env['ir.model.data'].create({
                'name': 'product_global_discount',
                'module': 'account_invoice_fixed_discount',
                'model': 'product.product',
                'res_id': discount_product.id,
            })

        return discount_product

    def write(self, vals):
        """Ensure global discount line is updated when saving."""
        res = super().write(vals)

        if 'global_discount_fixed' in vals:
            for move in self:
                if move.state != 'posted':
                    move._onchange_global_discount_fixed()

        return res

    @api.model_create_multi
    def create(self, vals_list):
        """Ensure global discount line is added when creating."""
        moves = super().create(vals_list)

        for move in moves:
            if move.global_discount_fixed and move.state != 'posted':
                move._onchange_global_discount_fixed()

        return moves
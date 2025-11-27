# Copyright 2017 ForgeFlow S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

from odoo import api, fields, models, Command
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
        discount_product = self._get_global_discount_product()
        discount_line = self.invoice_line_ids.filtered(
            lambda l: not l.display_type and l.product_id and
                      l.product_id.id == discount_product.id
        )

        if float_is_zero(self.global_discount_fixed, precision_rounding=currency.rounding):
            # Remove discount line if global discount is zero
            if discount_line:
                self.invoice_line_ids -= discount_line
            return

        if discount_line:
            # Update existing line
            discount_line.write({
                'price_unit': -abs(self.global_discount_fixed),
                'quantity': 1.0,
            })
        else:
            # Create new discount line at the end
            max_sequence = max([line.sequence for line in self.invoice_line_ids if line.sequence], default=10)

            self.invoice_line_ids = [Command.create({
                'product_id': discount_product.id,
                'name': 'Global Discount',
                'quantity': 1.0,
                'price_unit': -abs(self.global_discount_fixed),
                'sequence': max_sequence + 10,
            })]

    def _get_global_discount_product(self):
        """Get or create a product for global discount lines."""
        # Try to get existing product
        IrModelData = self.env['ir.model.data']
        product_xmlid = 'account_invoice_fixed_discount.product_global_discount'

        try:
            discount_product = self.env.ref(product_xmlid, raise_if_not_found=True)
        except:
            # Search by default_code if xml_id doesn't exist
            discount_product = self.env['product.product'].search([
                ('default_code', '=', 'GLOBAL_DISCOUNT')
            ], limit=1)

            if not discount_product:
                # Create the discount product
                discount_product = self.env['product.product'].create({
                    'name': 'Global Discount',
                    'type': 'service',
                    'invoice_policy': 'order',
                    'list_price': 0.0,
                    'default_code': 'GLOBAL_DISCOUNT',
                    'sale_ok': False,
                    'purchase_ok': False,
                })

                # Create external identifier
                IrModelData.create({
                    'name': 'product_global_discount',
                    'module': 'account_invoice_fixed_discount',
                    'model': 'product.product',
                    'res_id': discount_product.id,
                })

        # Always ensure taxes are cleared on the product
        discount_product.write({
            'tax_ids': [Command.clear()],
            'supplier_tax_ids': [Command.clear()],
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


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Override to ensure Global Discount product never gets taxes."""
        res = super()._onchange_product_id()

        # Check if this is the global discount product
        discount_product = self.env.ref(
            'account_invoice_fixed_discount.product_global_discount',
            raise_if_not_found=False
        )

        if discount_product and self.product_id and self.product_id.id == discount_product.id:
            # Force clear all taxes for global discount line
            self.tax_ids = [(5, 0, 0)]  # Clear all taxes

        return res
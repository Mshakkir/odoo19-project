# Copyright 2017 ForgeFlow S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

from odoo import api, fields, models, Command
from odoo.tools.float_utils import float_is_zero


class SaleOrder(models.Model):
    _inherit = "sale.order"

    global_discount_fixed = fields.Monetary(
        string="Global Discount (Fixed)",
        default=0.0,
        currency_field="currency_id",
        help="Apply a fixed discount to the entire order. This will be added as a separate discount line.",
        tracking=True,
    )

    @api.onchange('global_discount_fixed')
    def _onchange_global_discount_fixed(self):
        """Add or update a discount line for the global discount."""
        currency = self.currency_id or self.company_id.currency_id

        # Find existing discount line by checking for the specific default_code
        discount_line = self.order_line.filtered(
            lambda l: l.product_id and l.product_id.default_code == 'GLOBAL_DISCOUNT'
        )

        if float_is_zero(self.global_discount_fixed, precision_rounding=currency.rounding):
            # Remove discount line if global discount is zero
            if discount_line:
                self.order_line -= discount_line
            return

        # Get or create the discount product
        discount_product = self._get_global_discount_product()

        if discount_line:
            # Update existing line - clear taxes explicitly
            discount_line.product_id = discount_product.id  # Reset product
            discount_line.price_unit = -abs(self.global_discount_fixed)
            discount_line.product_uom_qty = 1.0
            discount_line.tax_id = False  # Force clear taxes
        else:
            # Create new line
            self.order_line = [Command.create({
                'product_id': discount_product.id,
                'name': 'Global Discount',
                'product_uom_qty': 1.0,
                'price_unit': -abs(self.global_discount_fixed),
                'sequence': 9999,
            })]

            # Immediately find and clear taxes on new line
            new_line = self.order_line.filtered(
                lambda l: l.product_id and l.product_id.default_code == 'GLOBAL_DISCOUNT'
            )
            if new_line:
                new_line.tax_id = False

    def _get_global_discount_product(self):
        """Get or create a product for global discount lines."""
        # Search by default_code
        discount_product = self.env['product.product'].search([
            ('default_code', '=', 'GLOBAL_DISCOUNT')
        ], limit=1)

        if discount_product:
            # Ensure product has no taxes
            if discount_product.taxes_id:
                discount_product.taxes_id = False
            if discount_product.supplier_taxes_id:
                discount_product.supplier_taxes_id = False
        else:
            # Create the discount product with no taxes
            discount_product = self.env['product.product'].create({
                'name': 'Global Discount',
                'type': 'service',
                'invoice_policy': 'order',
                'list_price': 0.0,
                'default_code': 'GLOBAL_DISCOUNT',
                'sale_ok': False,
                'purchase_ok': False,
            })
            # Clear taxes after creation
            discount_product.taxes_id = False
            discount_product.supplier_taxes_id = False

        return discount_product

    def write(self, vals):
        """Ensure global discount line is updated when saving."""
        res = super().write(vals)

        if 'global_discount_fixed' in vals:
            for order in self:
                order._onchange_global_discount_fixed()

        return res

    @api.model_create_multi
    def create(self, vals_list):
        """Ensure global discount line is added when creating."""
        orders = super().create(vals_list)

        for order in orders:
            if order.global_discount_fixed:
                order._onchange_global_discount_fixed()

        return orders

    def _prepare_invoice(self):
        """Pass the global discount to the invoice."""
        res = super()._prepare_invoice()
        res['global_discount_fixed'] = self.global_discount_fixed
        return res
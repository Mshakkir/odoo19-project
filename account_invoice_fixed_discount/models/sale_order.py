# Copyright 2017 ForgeFlow S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

# Copyright 2017 ForgeFlow S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

from odoo import api, fields, models
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

        # Find existing discount line
        discount_line = self.order_line.filtered(
            lambda l: l.display_type == 'line_section' and l.name and 'Global Discount' in l.name
        )

        # If no discount line exists but we're using a different approach, look for product-based discount line
        if not discount_line:
            discount_line = self.order_line.filtered(
                lambda l: l.product_id and l.product_id.id == self._get_global_discount_product().id
            )

        if float_is_zero(self.global_discount_fixed, precision_rounding=currency.rounding):
            # Remove discount line if global discount is zero
            if discount_line:
                self.order_line = [(2, discount_line.id, 0)]
            return

        # Create or update discount line
        discount_product = self._get_global_discount_product()

        if discount_line:
            # Update existing line
            discount_line.write({
                'price_unit': -abs(self.global_discount_fixed),
                'product_uom_qty': 1.0,
            })
        else:
            # Create new discount line at the end
            self.order_line = [(0, 0, {
                'product_id': discount_product.id,
                'name': 'Global Discount',
                'product_uom_qty': 1.0,
                'price_unit': -abs(self.global_discount_fixed),
                'tax_id': [(6, 0, [])],  # No taxes on discount line
                'sequence': 9999,  # Put it at the end
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
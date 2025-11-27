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
        help="Apply a fixed discount to the entire order.",
        tracking=True,
    )

    @api.onchange('global_discount_fixed')
    def _onchange_global_discount_fixed(self):
        """Create or update global discount line."""
        currency = self.currency_id or self.company_id.currency_id

        discount_line = self.order_line.filtered(
            lambda l: l.product_id and l.product_id.default_code == "GLOBAL_DISCOUNT"
        )

        if float_is_zero(self.global_discount_fixed, precision_rounding=currency.rounding):
            if discount_line:
                self.order_line -= discount_line
            return

        discount_product = self._get_global_discount_product()

        if discount_line:
            discount_line.write({
                "product_id": discount_product.id,
                "price_unit": -abs(self.global_discount_fixed),
                "product_uom_qty": 1.0,
                "tax_id": [Command.clear()],
            })
        else:
            self.order_line = [Command.create({
                "product_id": discount_product.id,
                "name": "Global Discount",
                "product_uom_qty": 1.0,
                "price_unit": -abs(self.global_discount_fixed),
                "tax_id": [Command.clear()],
                "sequence": 9999,
            })]

    def _get_global_discount_product(self):
        """Get/Create the global discount product (no taxes)."""
        product = self.env["product.product"].search([
            ("default_code", "=", "GLOBAL_DISCOUNT")
        ], limit=1)

        if not product:
            product = self.env["product.product"].create({
                "name": "Global Discount",
                "type": "service",
                "invoice_policy": "order",
                "list_price": 0.0,
                "default_code": "GLOBAL_DISCOUNT",
                "sale_ok": False,
                "purchase_ok": False,
            })

        product.taxes_id = False
        product.supplier_taxes_id = False
        return product

    def write(self, vals):
        res = super().write(vals)
        if "global_discount_fixed" in vals:
            for order in self:
                order._onchange_global_discount_fixed()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        for order in orders:
            if order.global_discount_fixed:
                order._onchange_global_discount_fixed()
        return orders

    def _prepare_invoice(self):
        res = super()._prepare_invoice()
        res["global_discount_fixed"] = self.global_discount_fixed
        return res

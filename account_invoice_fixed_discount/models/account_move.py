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
        tracking=True,
        help="Apply a fixed discount on invoice.",
        states={'posted': [('readonly', True)]}
    )

    @api.onchange('global_discount_fixed')
    def _onchange_global_discount_fixed(self):
        if not self.invoice_line_ids:
            return

        currency = self.currency_id or self.company_id.currency_id
        discount_product = self._get_global_discount_product()

        discount_line = self.invoice_line_ids.filtered(
            lambda l: l.product_id.id == discount_product.id
        )

        if float_is_zero(self.global_discount_fixed, precision_rounding=currency.rounding):
            if discount_line:
                self.invoice_line_ids -= discount_line
            return

        if discount_line:
            discount_line.write({
                "price_unit": -abs(self.global_discount_fixed),
                "quantity": 1.0,
                "tax_ids": [Command.clear()],
            })
        else:
            max_seq = max(self.invoice_line_ids.mapped("sequence") or [10])
            self.invoice_line_ids = [Command.create({
                "product_id": discount_product.id,
                "name": "Global Discount",
                "quantity": 1.0,
                "price_unit": -abs(self.global_discount_fixed),
                "sequence": max_seq + 10,
                "tax_ids": [Command.clear()],
            })]

    def _get_global_discount_product(self):
        """Re-use or create product without taxes."""
        IrModelData = self.env["ir.model.data"]
        try:
            product = self.env.ref(
                "account_invoice_fixed_discount.product_global_discount",
                raise_if_not_found=True
            )
        except:
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

                IrModelData.create({
                    "name": "product_global_discount",
                    "module": "account_invoice_fixed_discount",
                    "model": "product.product",
                    "res_id": product.id,
                })

        product.taxes_id = [Command.clear()]
        product.supplier_taxes_id = [Command.clear()]
        return product

    def write(self, vals):
        res = super().write(vals)
        if "global_discount_fixed" in vals:
            for move in self:
                if move.state != "posted":
                    move._onchange_global_discount_fixed()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        for move in moves:
            if move.global_discount_fixed and move.state != "posted":
                move._onchange_global_discount_fixed()
        return moves


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.onchange('product_id')
    def _onchange_product_id(self):
        res = super()._onchange_product_id()
        try:
            discount_product = self.env.ref(
                "account_invoice_fixed_discount.product_global_discount",
                raise_if_not_found=False
            )
            if discount_product and self.product_id.id == discount_product.id:
                self.tax_ids = [Command.clear()]
        except:
            pass
        return res

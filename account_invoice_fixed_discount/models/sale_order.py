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

    # ------------------------------------------------------------
    #   MAIN ONCHANGE DISCOUNT FUNCTION
    # ------------------------------------------------------------
    @api.onchange('global_discount_fixed')
    def _onchange_global_discount_fixed(self):
        """Create or update global discount line correctly with taxes."""
        currency = self.currency_id or self.company_id.currency_id

        # Find discount line
        discount_line = self.order_line.filtered(
            lambda l: l.product_id and l.product_id.default_code == "GLOBAL_DISCOUNT"
        )

        # If discount is 0 → remove line
        if float_is_zero(self.global_discount_fixed, precision_rounding=currency.rounding):
            if discount_line:
                self.order_line -= discount_line
            return

        # Get discount product
        discount_product = self._get_global_discount_product()

        # Fetch correct taxes (VERY IMPORTANT)
        discount_taxes = self._get_discount_taxes()

        discount_vals = {
            "product_id": discount_product.id,
            "name": "Global Discount",
            "product_uom_qty": 1.0,
            "price_unit": -abs(self.global_discount_fixed),
            "tax_ids": [Command.set(discount_taxes)],
            "sequence": 9999,
        }

        # Update if exists else create
        if discount_line:
            discount_line.write(discount_vals)
        else:
            self.order_line = [Command.create(discount_vals)]

    # ------------------------------------------------------------
    #   GET SAME TAXES AS OTHER LINES FOR CORRECT VAT CALCULATION
    # ------------------------------------------------------------
    def _get_discount_taxes(self):
        """Return VAT taxes from any taxable line so VAT recalculates properly."""
        taxable_lines = self.order_line.filtered(lambda l: l.tax_ids)
        if taxable_lines:
            return taxable_lines[0].tax_ids.ids  # Take the first VAT group
        return []  # no taxes found

    # ------------------------------------------------------------
    #   GET / CREATE DISCOUNT PRODUCT
    # ------------------------------------------------------------
    def _get_global_discount_product(self):
        """Get or create the discount service product."""
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

        # Do not force-clear taxes here
        # Taxes will be dynamically assigned on order_line
        return product

    # ------------------------------------------------------------
    #   WRITE OVERRIDE (Recompute discount lines if field changed)
    # ------------------------------------------------------------
    def write(self, vals):
        res = super().write(vals)
        if "global_discount_fixed" in vals:
            for order in self:
                order._onchange_global_discount_fixed()
        return res

    # ------------------------------------------------------------
    #   CREATE OVERRIDE (Recompute discount on creation)
    # ------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        for order in orders:
            if order.global_discount_fixed:
                order._onchange_global_discount_fixed()
        return orders

    # ------------------------------------------------------------
    #   PASS DISCOUNT VALUE TO INVOICE
    # ------------------------------------------------------------
    def _prepare_invoice(self):
        res = super()._prepare_invoice()
        res["global_discount_fixed"] = self.global_discount_fixed
        return res

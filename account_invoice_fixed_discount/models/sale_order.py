# Copyright 2017 ForgeFlow S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    amount_before_discount = fields.Monetary(
        string="Amount Before Discount",
        compute="_compute_discount_amounts",
        store=True,
        help="Total amount before applying any discounts"
    )

    amount_total_discount = fields.Monetary(
        string="Total Discount",
        compute="_compute_discount_amounts",
        store=True,
        help="Total discount amount applied to all order lines"
    )

    @api.depends('order_line.price_unit', 'order_line.product_uom_qty', 'order_line.discount_fixed')
    def _compute_discount_amounts(self):
        """Calculate amount before discount and total discount amount."""
        for order in self:
            amount_before_discount = 0.0
            amount_total_discount = 0.0

            for line in order.order_line:
                # Calculate line subtotal before discount
                line_before_discount = line.price_unit * line.product_uom_qty
                amount_before_discount += line_before_discount

                # Calculate discount amount for this line
                if line.discount_fixed:
                    amount_total_discount += line.discount_fixed
                elif line.discount:
                    # Calculate discount from percentage
                    discount_amount = line_before_discount * (line.discount / 100)
                    amount_total_discount += discount_amount

            order.amount_before_discount = amount_before_discount
            order.amount_total_discount = amount_total_discount
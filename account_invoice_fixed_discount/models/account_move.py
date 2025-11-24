# Copyright 2017 ForgeFlow S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

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
        help="Total discount amount applied to all invoice lines"
    )

    @api.depends('invoice_line_ids.price_unit', 'invoice_line_ids.quantity', 'invoice_line_ids.discount_fixed')
    def _compute_discount_amounts(self):
        """Calculate amount before discount and total discount amount."""
        for move in self:
            amount_before_discount = 0.0
            amount_total_discount = 0.0

            for line in move.invoice_line_ids:
                # Calculate line subtotal before discount
                line_before_discount = line.price_unit * line.quantity
                amount_before_discount += line_before_discount

                # Calculate discount amount for this line
                if line.discount_fixed:
                    amount_total_discount += line.discount_fixed
                elif line.discount:
                    # Calculate discount from percentage
                    discount_amount = line_before_discount * (line.discount / 100)
                    amount_total_discount += discount_amount

            move.amount_before_discount = amount_before_discount
            move.amount_total_discount = amount_total_discount
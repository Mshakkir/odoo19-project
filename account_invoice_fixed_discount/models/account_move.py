from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    global_discount_amount = fields.Monetary(
        string="Global Discount",
        default=0.0,
        currency_field="currency_id",
        help="Fixed discount applied on the total untaxed."
    )

    amount_after_discount = fields.Monetary(
        string="Total After Discount",
        compute="_compute_after_discount"
    )

    @api.depends('amount_untaxed', 'global_discount_amount')
    def _compute_after_discount(self):
        for inv in self:
            inv.amount_after_discount = inv.amount_untaxed - inv.global_discount_amount

    @api.depends('invoice_line_ids.price_total', 'global_discount_amount')
    def _compute_amount(self):
        """Override final totals"""
        super()._compute_amount()

        for inv in self:
            inv.amount_untaxed -= inv.global_discount_amount
            inv.amount_total = inv.amount_untaxed + inv.amount_tax

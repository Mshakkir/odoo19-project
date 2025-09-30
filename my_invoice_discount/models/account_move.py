from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    discount_type = fields.Selection([
        ('amount', 'Fixed Amount'),
        ('percent', 'Percentage'),
    ], string="Discount Type", default='amount')

    discount_value = fields.Float(string="Discount Value", default=0.0)
    total_discount = fields.Monetary(
        string="Discount",
        currency_field='currency_id',
        compute="_compute_total_discount",
        store=True,
    )
    freight_amount = fields.Monetary(
        string="Freight",
        currency_field='currency_id',
    )

    @api.depends('line_ids.price_total', 'discount_type', 'discount_value')
    def _compute_total_discount(self):
        for move in self:
            if move.discount_type == 'percent':
                move.total_discount = (move.amount_untaxed * move.discount_value) / 100
            else:
                move.total_discount = move.discount_value

    @api.depends('invoice_line_ids.price_subtotal', 'invoice_line_ids.tax_ids', 'freight_amount', 'total_discount')
    def _compute_amount(self):
        super(AccountMove, self)._compute_amount()
        for move in self:
            # Apply discount to untaxed amount
            untaxed_amount = move.amount_untaxed - (move.total_discount or 0.0)

            # Recalculate VAT based on discounted amount
            tax_amount = 0.0
            for line in move.invoice_line_ids:
                line_subtotal = line.price_subtotal - (move.total_discount or 0.0) * (
                            line.price_subtotal / move.amount_untaxed) if move.amount_untaxed else line.price_subtotal
                tax_amount += line_subtotal * sum(t.amount for t in line.tax_ids) / 100.0

            move.amount_untaxed = untaxed_amount
            move.amount_tax = tax_amount
            move.amount_total = untaxed_amount + tax_amount + (move.freight_amount or 0.0)

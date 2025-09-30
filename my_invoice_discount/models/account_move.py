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
        super(AccountMove, self)._compute_amount()  # Call Odoo's default calculation first
        for move in self:
            # Recalculate amounts with discount and freight
            move.amount_untaxed -= move.total_discount or 0.0
            move.amount_total = move.amount_untaxed + move.amount_tax + (move.freight_amount or 0.0)

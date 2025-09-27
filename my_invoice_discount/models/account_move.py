from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    discount_amount = fields.Monetary(
        string="Discount Amount",
        currency_field='currency_id',
    )
    freight_amount = fields.Monetary(
        string="Freight Amount",
        currency_field='currency_id',
    )

    @api.depends('line_ids.price_total', 'discount_amount', 'freight_amount')
    def _compute_amount(self):
        super(AccountMove, self)._compute_amount()
        for record in self:
            record.amount_total = record.amount_total - (record.discount_amount or 0.0) + (record.freight_amount or 0.0)

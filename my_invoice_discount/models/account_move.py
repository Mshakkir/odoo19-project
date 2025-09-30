# from odoo import models, fields, api
#
# class AccountMove(models.Model):
#     _inherit = 'account.move'
#
#     discount_amount = fields.Monetary(
#         string="Discount Amount",
#         currency_field='currency_id',
#     )
#     freight_amount = fields.Monetary(
#         string="Freight Amount",
#         currency_field='currency_id',
#     )
#
#     @api.depends('line_ids.price_total', 'discount_amount', 'freight_amount')
#     def _compute_amount(self):
#         super(AccountMove, self)._compute_amount()
#         for record in self:
#             record.amount_total = record.amount_total - (record.discount_amount or 0.0) + (record.freight_amount or 0.0)
from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    discount_type = fields.Selection(
        [('amount', 'Amount'), ('percent', 'Percentage')],
        string="Discount Type",
        default='amount'
    )
    discount_amount = fields.Float(string="Discount Value", default=0.0)
    freight_amount = fields.Monetary(string="Freight", default=0.0, currency_field='currency_id')

    @api.depends('line_ids.price_total', 'discount_type', 'discount_value', 'freight_amount')
    def _compute_amount(self):
        super()._compute_amount()
        for record in self:
            total = record.amount_untaxed
            if record.discount_type == 'percent':
                discount = total * (record.discount_value / 100.0)
            else:
                discount = record.discount_amount

            record.amount_total = total - discount + record.amount_tax + (record.freight_amount or 0.0)

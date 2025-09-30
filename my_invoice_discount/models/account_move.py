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

    @api.depends('line_ids.price_total', 'total_discount', 'freight_amount')
    def _compute_amount(self):
        super(AccountMove, self)._compute_amount()
        for record in self:
            record.amount_total = (
                record.amount_total - (record.total_discount or 0.0) + (record.freight_amount or 0.0)
            )

# from odoo import models, fields, api
#
# class SaleOrder(models.Model):
#     _inherit = 'sale.order'
#
#     discount_amount = fields.Monetary(
#         string="Discount",
#         default=0.0,
#         currency_field='currency_id',
#     )
#     freight_amount = fields.Monetary(
#         string="Freight",
#         default=0.0,
#         currency_field='currency_id',
#     )
#
#     def _prepare_invoice(self):
#         invoice_vals = super()._prepare_invoice()
#         invoice_vals.update({
#             'discount_amount': self.discount_amount,
#             'freight_amount': self.freight_amount,
#         })
#         return invoice_vals
from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    discount_type = fields.Selection(
        [('amount', 'Amount'), ('percent', 'Percentage')],
        string="Discount Type",
        default='amount'
    )
    discount_amount = fields.Float(string="Discount Value", default=0.0)
    freight_amount = fields.Monetary(string="Freight", default=0.0, currency_field='currency_id')

    def _prepare_invoice(self):
        invoice_vals = super()._prepare_invoice()
        invoice_vals.update({
            'discount_type': self.discount_type,
            'discount_value': self.discount_amount,
            'freight_amount': self.freight_amount,
        })
        return invoice_vals

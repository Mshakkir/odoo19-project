# from odoo import models, fields, api
# from odoo.tools.amount_to_text_en import amount_to_text
# from num2words import num2words
#
#
# class AccountMove(models.Model):
#     _inherit = "account.move"
#
#     discount = fields.Float(string="Discount")
#
#     # Computed fields for amount in words (both English and Arabic)
#     amount_to_text_en = fields.Char(string="Amount in Words (English)", compute="_compute_amount_words", store=True)
#     amount_to_text_ar = fields.Char(string="Amount in Words (Arabic)", compute="_compute_amount_words", store=True)
#
#     @api.depends("amount_total", "currency_id")
#     def _compute_amount_words(self):
#         for rec in self:
#             if rec.amount_total:
#                 # English amount in words
#                 rec.amount_to_text_en = amount_to_text(
#                     rec.amount_total, "en", rec.currency_id.name
#                 ).replace(" and Zero", "")
#
#                 # Arabic amount in words using num2words
#                 try:
#                     arabic_words = num2words(rec.amount_total, lang="ar")
#                     rec.amount_to_text_ar = f"{arabic_words} {rec.currency_id.symbol or rec.currency_id.name}"
#                 except Exception:
#                     rec.amount_to_text_ar = ""
#             else:
#                 rec.amount_to_text_en = ""
#                 rec.amount_to_text_ar = ""
#
#
# class SaleOrder(models.Model):
#     _inherit = "sale.order"
#
#     discount = fields.Float(string="Discount")
#
#     def _prepare_invoice(self):
#         invoice_vals = super()._prepare_invoice()
#         invoice_vals["discount"] = self.discount
#         return invoice_vals

from odoo import models, fields

class AccountMove(models.Model):
    _inherit = "account.move"

    discount = fields.Float(string="Discount")

class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _prepare_invoice(self):
        invoice_vals = super()._prepare_invoice()
        invoice_vals['discount'] = self.discount
        return invoice_vals

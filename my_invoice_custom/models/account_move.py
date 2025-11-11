# from odoo import models, fields
#
# class AccountMove(models.Model):
#     _inherit = "account.move"
#
#     discount = fields.Float(string="Discount")
#
# class SaleOrder(models.Model):
#     _inherit = "sale.order"
#
#     def _prepare_invoice(self):
#         invoice_vals = super()._prepare_invoice()
#         invoice_vals['discount'] = self.discount
#         return invoice_vals


from odoo import models
from num2words import num2words


class AccountMove(models.Model):
    _inherit = 'account.move'

    def amount_to_text_arabic(self, amount):
        """Convert amount to Arabic words"""
        try:
            # Convert number to Arabic words
            words = num2words(amount, lang='ar', to='currency', currency='SAR')
            return words
        except:
            # Fallback if num2words doesn't work
            return self.currency_id.with_context(lang='ar_001').amount_to_text(amount)
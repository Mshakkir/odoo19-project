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


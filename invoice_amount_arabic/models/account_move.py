# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

try:
    from num2words import num2words

    NUM2WORDS_AVAILABLE = True
except ImportError:
    NUM2WORDS_AVAILABLE = False
    _logger.warning("num2words library not installed. Arabic amount conversion will not work.")


class AccountMove(models.Model):
    _inherit = 'account.move'

    amount_to_text_ar = fields.Char(
        string='Amount in Arabic Words',
        compute='_compute_amount_to_text_ar',
        store=False,
        help='Total amount converted to Arabic words'
    )

    @api.depends('amount_total', 'currency_id')
    def _compute_amount_to_text_ar(self):
        """
        Convert the invoice total amount to Arabic words.
        Handles:
        - Integer and decimal parts
        - Different currencies (SAR, USD, EUR, etc.)
        - Edge cases (zero, negative, very large numbers)
        - Missing num2words library
        """
        for record in self:
            if not NUM2WORDS_AVAILABLE:
                record.amount_to_text_ar = 'مكتبة التحويل غير متوفرة'
                continue

            if not record.amount_total:
                record.amount_to_text_ar = 'صفر'
                continue

            try:
                amount = abs(record.amount_total)  # Handle negative amounts
                currency_name = record.currency_id.name or 'SAR'

                # Split amount into integer and decimal parts
                integer_part = int(amount)
                decimal_part = int(round((amount - integer_part) * 100))

                # Handle zero amount
                if integer_part == 0 and decimal_part == 0:
                    record.amount_to_text_ar = 'صفر'
                    continue

                # Convert integer part to Arabic words
                if integer_part > 0:
                    amount_text = num2words(integer_part, lang='ar')
                else:
                    amount_text = ''

                # Add currency name in Arabic based on currency type
                currency_config = self._get_currency_arabic_name(currency_name, integer_part)

                if integer_part > 0:
                    amount_text += f' {currency_config["main"]}'

                # Add decimal part if exists
                if decimal_part > 0:
                    decimal_text = num2words(decimal_part, lang='ar')
                    if integer_part > 0:
                        amount_text += ' و'
                    amount_text += f' {decimal_text} {currency_config["sub"]}'

                # Add prefix for negative amounts
                if record.amount_total < 0:
                    amount_text = 'سالب ' + amount_text

                record.amount_to_text_ar = amount_text

            except Exception as e:
                _logger.error(f"Error converting amount to Arabic words: {str(e)}")
                record.amount_to_text_ar = f'خطأ في التحويل'

    def _get_currency_arabic_name(self, currency_code, amount):
        """
        Returns Arabic currency names with proper grammar
        based on the amount (singular, dual, plural)
        """
        currency_map = {
            'SAR': {
                'main': self._get_arabic_currency_form(amount, 'ريال سعودي', 'ريالان سعوديان', 'ريالات سعودية',
                                                       'ريال سعودي'),
                'sub': 'هللة'
            },
            'USD': {
                'main': self._get_arabic_currency_form(amount, 'دولار أمريكي', 'دولاران أمريكيان', 'دولارات أمريكية',
                                                       'دولار أمريكي'),
                'sub': 'سنت'
            },
            'EUR': {
                'main': self._get_arabic_currency_form(amount, 'يورو', 'يوروان', 'يوروات', 'يورو'),
                'sub': 'سنت'
            },
            'AED': {
                'main': self._get_arabic_currency_form(amount, 'درهم إماراتي', 'درهمان إماراتيان', 'دراهم إماراتية',
                                                       'درهم إماراتي'),
                'sub': 'فلس'
            },
            'KWD': {
                'main': self._get_arabic_currency_form(amount, 'دينار كويتي', 'ديناران كويتيان', 'دنانير كويتية',
                                                       'دينار كويتي'),
                'sub': 'فلس'
            },
            'BHD': {
                'main': self._get_arabic_currency_form(amount, 'دينار بحريني', 'ديناران بحرينيان', 'دنانير بحرينية',
                                                       'دينار بحريني'),
                'sub': 'فلس'
            },
            'OMR': {
                'main': self._get_arabic_currency_form(amount, 'ريال عماني', 'ريالان عمانيان', 'ريالات عمانية',
                                                       'ريال عماني'),
                'sub': 'بيسة'
            },
            'QAR': {
                'main': self._get_arabic_currency_form(amount, 'ريال قطري', 'ريالان قطريان', 'ريالات قطرية',
                                                       'ريال قطري'),
                'sub': 'درهم'
            },
        }

        return currency_map.get(currency_code, {
            'main': currency_code,
            'sub': 'وحدة فرعية'
        })

    def _get_arabic_currency_form(self, amount, singular, dual, small_plural, large_plural):
        """
        Returns appropriate Arabic currency form based on number
        Arabic has 4 forms:
        - Singular (1)
        - Dual (2)
        - Small plural (3-10)
        - Large plural (11+)
        """
        if amount == 1:
            return singular
        elif amount == 2:
            return dual
        elif 3 <= amount <= 10:
            return small_plural
        else:
            return large_plural

    def get_amount_in_words_bilingual(self):
        """
        Returns amount in words in both English and Arabic
        Useful for templates that need both languages
        """
        self.ensure_one()

        english_text = self.currency_id.amount_to_text(self.amount_total)
        arabic_text = self.amount_to_text_ar or 'غير متاح'

        return {
            'english': english_text,
            'arabic': arabic_text,
            'bilingual': f'{english_text} / {arabic_text}',
            'english_only': f'{english_text} Only',
            'arabic_only': f'{arabic_text} فقط لا غير'
        }

    def action_check_arabic_conversion(self):
        """
        Manual action to test Arabic conversion
        Useful for debugging
        """
        self.ensure_one()
        if not NUM2WORDS_AVAILABLE:
            raise UserError(_('num2words library is not installed. Please install it using: pip install num2words'))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Amount in Arabic'),
                'message': f'{self.amount_to_text_ar}',
                'sticky': False,
                'type': 'info',
            }
        }
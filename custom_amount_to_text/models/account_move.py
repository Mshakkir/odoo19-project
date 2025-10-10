from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = "account.move"

    amount_to_text_ar = fields.Char(
        string="Amount in Words (Arabic)",
        compute="_compute_amount_words",
        store=True
    )

    @api.depends("amount_total")
    def _compute_amount_words(self):
        for rec in self:
            total = rec.amount_total or 0
            try:
                rec.amount_to_text_ar = self._convert_number_to_arabic_text(total)
            except Exception as e:
                rec.amount_to_text_ar = str(total)  # fallback
                _logger.exception("Error converting amount to Arabic text: %s", e)

    def _convert_number_to_arabic_text(self, number):
        units = ["صفر", "واحد", "اثنان", "ثلاثة", "أربعة", "خمسة", "ستة", "سبعة", "ثمانية", "تسعة"]
        tens = ["", "عشرة", "عشرون", "ثلاثون", "أربعون", "خمسون", "ستون", "سبعون", "ثمانون", "تسعون"]

        n = int(number)
        if n < 10:
            return units[n]
        elif n < 100:
            t, u = divmod(n, 10)
            return f"{units[u]} و {tens[t]}" if u else tens[t]
        else:
            return f"{n} ريال"

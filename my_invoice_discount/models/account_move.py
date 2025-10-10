# my_invoice_discount/models/account_move.py
from odoo import models, fields, api
from odoo.tools.amount_to_text_en import amount_to_text


class AccountMove(models.Model):
    _inherit = 'account.move'

    # --- Discount & Freight fields (existing) ---
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

    # --- Amount in words (Arabic) ---
    amount_to_text_ar = fields.Char(
        string="Amount in Words (Arabic)",
        compute="_compute_amount_words",
        store=True,
    )
    amount_to_text_en = fields.Char(
        string="Amount in Words (English)",
        compute="_compute_amount_words",
        store=True,
    )

    # ---------- discount computations (your existing code) ----------
    @api.depends('line_ids.price_total', 'discount_type', 'discount_value')
    def _compute_total_discount(self):
        for move in self:
            if move.discount_type == 'percent':
                move.total_discount = (move.amount_untaxed * move.discount_value) / 100
            else:
                move.total_discount = move.discount_value

    @api.depends('invoice_line_ids.price_subtotal', 'invoice_line_ids.tax_ids', 'freight_amount', 'total_discount')
    def _compute_amount(self):
        super(AccountMove, self)._compute_amount()
        for move in self:
            untaxed_amount = move.amount_untaxed - (move.total_discount or 0.0)

            tax_amount = 0.0
            for line in move.invoice_line_ids:
                if move.amount_untaxed:
                    line_subtotal = line.price_subtotal - (move.total_discount or 0.0) * (
                        line.price_subtotal / move.amount_untaxed)
                else:
                    line_subtotal = line.price_subtotal
                tax_amount += line_subtotal * sum(t.amount for t in line.tax_ids) / 100.0

            move.amount_untaxed = untaxed_amount
            move.amount_tax = tax_amount
            move.amount_total = untaxed_amount + tax_amount + (move.freight_amount or 0.0)

    # ---------- Arabic converter helpers ----------
    def _three_digits_to_ar(self, n):
        # Handles 0..999
        units = ["صفر", "واحد", "اثنان", "ثلاثة", "أربعة", "خمسة", "ستة", "سبعة", "ثمانية", "تسعة"]
        teens = {
            10: "عشرة", 11: "أحد عشر", 12: "اثنا عشر", 13: "ثلاثة عشر", 14: "أربعة عشر",
            15: "خمسة عشر", 16: "ستة عشر", 17: "سبعة عشر", 18: "ثمانية عشر", 19: "تسعة عشر"
        }
        tens = ["", "", "عشرون", "ثلاثون", "أربعون", "خمسون", "ستون", "سبعون", "ثمانون", "تسعون"]
        hundreds = [None, "مائة", "مائتان", "ثلاثمائة", "أربعمائة", "خمسمائة", "ستمائة", "سبعمائة", "ثمانمائة", "تسعمائة"]

        parts = []
        h = n // 100
        rem = n % 100
        if h:
            parts.append(hundreds[h])
        if rem:
            if rem < 10:
                parts.append(units[rem])
            elif rem < 20:
                parts.append(teens[rem])
            else:
                t = rem // 10
                u = rem % 10
                if u:
                    parts.append(units[u] + " و " + tens[t])
                else:
                    parts.append(tens[t])
        return " و ".join(parts)

    def _int_to_ar(self, n):
        # Convert integer (0 <= n) into Arabic words (supports up to billions)
        if n == 0:
            return "صفر"
        parts = []
        groups = [
            (1000000000, 'مليار', 'مليارات', 'ملياران'),
            (1000000, 'مليون', 'ملايين', 'مليونان'),
            (1000, 'ألف', 'آلاف', 'ألفان'),
        ]
        remainder = n
        for value, name, plural, dual in groups:
            count = remainder // value
            if count:
                if count == 1:
                    parts.append(name)
                elif count == 2:
                    parts.append(dual)
                elif 3 <= count <= 10:
                    parts.append(self._three_digits_to_ar(count) + " " + plural)
                else:
                    # > 10: use number + singular (pragmatic)
                    parts.append(self._three_digits_to_ar(count) + " " + name)
                remainder = remainder % value
        if remainder:
            parts.append(self._three_digits_to_ar(remainder))
        return " و ".join(parts)

    def _currency_names_ar(self, rec):
        # Choose Arabic unit & subunit names heuristically from currency name/symbol
        cname = (rec.currency_id.name or "").lower()
        sym = (rec.currency_id.symbol or "").lower()
        # Saudi Riyal
        if "riy" in cname or "sar" in cname or "ريال" in cname or "ر.س" in sym:
            return ("ريال", "هللة")
        # UAE Dirham
        if "dirham" in cname or "aed" in cname or "درهم" in cname:
            return ("درهم", "فلس")
        # Kuwaiti Dinar
        if "dinar" in cname or "kwd" in cname or "دينار" in cname:
            return ("دينار", "فلس")
        # Default fallback: use currency name + "سنت" for fraction
        unit = rec.currency_id.name or ""
        return (unit, "سنت")

    # ---------- compute method ----------
    @api.depends('amount_total', 'currency_id')
    def _compute_amount_words(self):
        for rec in self:
            try:
                amt = float(rec.amount_total or 0.0)
            except Exception:
                amt = 0.0
            negative = amt < 0
            amt = abs(amt)
            integer_part = int(amt)
            fraction_part = int(round((amt - integer_part) * 100))  # two decimals (halalas)
            # Convert integer and fraction
            try:
                int_words = self._int_to_ar(integer_part) if integer_part >= 0 else ""
            except Exception:
                int_words = ""
            try:
                frac_words = self._int_to_ar(fraction_part) if fraction_part else ""
            except Exception:
                frac_words = ""
            # currency names
            unit_ar, frac_unit_ar = self._currency_names_ar(rec)
            # Build Arabic phrase
            if integer_part == 0 and fraction_part == 0:
                ar_phrase = f"صفر {unit_ar}"
            elif fraction_part == 0:
                ar_phrase = f"{int_words} {unit_ar}"
            else:
                ar_phrase = f"{int_words} {unit_ar} و {frac_words} {frac_unit_ar}"
            if negative:
                ar_phrase = f"سالب {ar_phrase}"
            rec.amount_to_text_ar = ar_phrase

            # English (fallback / helpful): use odoo helper (stored so template can use o.amount_to_text_en)
            try:
                rec.amount_to_text_en = amount_to_text(rec.amount_total, 'en', rec.currency_id.name)
            except Exception:
                rec.amount_to_text_en = ""


# from odoo import models, fields, api
#
# class AccountMove(models.Model):
#     _inherit = 'account.move'
#
#     discount_type = fields.Selection([
#         ('amount', 'Fixed Amount'),
#         ('percent', 'Percentage'),
#     ], string="Discount Type", default='amount')
#
#     discount_value = fields.Float(string="Discount Value", default=0.0)
#     total_discount = fields.Monetary(
#         string="Discount",
#         currency_field='currency_id',
#         compute="_compute_total_discount",
#         store=True,
#     )
#     freight_amount = fields.Monetary(
#         string="Freight",
#         currency_field='currency_id',
#     )
#
#     @api.depends('line_ids.price_total', 'discount_type', 'discount_value')
#     def _compute_total_discount(self):
#         for move in self:
#             if move.discount_type == 'percent':
#                 move.total_discount = (move.amount_untaxed * move.discount_value) / 100
#             else:
#                 move.total_discount = move.discount_value
#
#     @api.depends('invoice_line_ids.price_subtotal', 'invoice_line_ids.tax_ids', 'freight_amount', 'total_discount')
#     def _compute_amount(self):
#         super(AccountMove, self)._compute_amount()
#         for move in self:
#             # Apply discount to untaxed amount
#             untaxed_amount = move.amount_untaxed - (move.total_discount or 0.0)
#
#             # Recalculate VAT based on discounted amount
#             tax_amount = 0.0
#             for line in move.invoice_line_ids:
#                 line_subtotal = line.price_subtotal - (move.total_discount or 0.0) * (
#                             line.price_subtotal / move.amount_untaxed) if move.amount_untaxed else line.price_subtotal
#                 tax_amount += line_subtotal * sum(t.amount for t in line.tax_ids) / 100.0
#
#             move.amount_untaxed = untaxed_amount
#             move.amount_tax = tax_amount
#             move.amount_total = untaxed_amount + tax_amount + (move.freight_amount or 0.0)

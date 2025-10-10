from odoo import models, fields, api
from odoo.tools.amount_to_text_en import amount_to_text
from num2words import num2words

class AccountMove(models.Model):
    _inherit = 'account.move'

    # === Discount & Freight ===
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

    # === Amount in Words ===
    amount_to_text_en = fields.Char(
        string="Amount in Words (English)",
        compute="_compute_amount_words",
        store=True
    )
    amount_to_text_ar = fields.Char(
        string="Amount in Words (Arabic)",
        compute="_compute_amount_words",
        store=True
    )

    # === Compute Methods ===
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
            # Apply discount to untaxed amount
            untaxed_amount = move.amount_untaxed - (move.total_discount or 0.0)

            # Recalculate VAT based on discounted amount
            tax_amount = 0.0
            for line in move.invoice_line_ids:
                line_subtotal = line.price_subtotal - (move.total_discount or 0.0) * (
                        line.price_subtotal / move.amount_untaxed) if move.amount_untaxed else line.price_subtotal
                tax_amount += line_subtotal * sum(t.amount for t in line.tax_ids) / 100.0

            move.amount_untaxed = untaxed_amount
            move.amount_tax = tax_amount
            move.amount_total = untaxed_amount + tax_amount + (move.freight_amount or 0.0)

    @api.depends('amount_total')
    def _compute_amount_words(self):
        for rec in self:
            # English amount
            rec.amount_to_text_en = amount_to_text(rec.amount_total, 'en', rec.currency_id.name).replace(' and Zero', '')
            # Arabic amount
            try:
                arabic_words = num2words(rec.amount_total, lang='ar')
                rec.amount_to_text_ar = f"{arabic_words} {rec.currency_id.name}"
            except NotImplementedError:
                rec.amount_to_text_ar = ""
#

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

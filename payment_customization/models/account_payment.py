# -*- coding: utf-8 -*-

from odoo import api, fields, models


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    # Add new memo field
    memo_new = fields.Text(
        string='Memo',
        help='Additional memo or notes for this payment'
    )

    # Add advance payment checkbox
    is_advance_payment = fields.Boolean(
        string='Advance Payment',
        default=False,
        help='Check this box if this is an advance payment'
    )

    # Expose company currency so the view can compare currency_id == company_currency_id
    company_currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        string='Company Currency',
        store=False,
    )

    # Manual exchange rate: 1 [payment currency] = X [company currency]
    manual_currency_exchange_rate = fields.Float(
        string='Exchange Rate',
        digits=(12, 6),
        default=1.0,
        help='Rate: 1 [payment currency] = ? [company currency]'
    )

    # Helper char fields to show currency names in the rate label
    payment_currency_name = fields.Char(
        compute='_compute_currency_display',
        string='Payment Currency Name',
    )
    company_currency_name = fields.Char(
        compute='_compute_currency_display',
        string='Company Currency Name',
    )

    @api.depends('currency_id', 'company_id')
    def _compute_currency_display(self):
        for rec in self:
            rec.payment_currency_name = rec.currency_id.name or ''
            rec.company_currency_name = rec.company_id.currency_id.name or ''

    @api.onchange('partner_id')
    def _onchange_partner_id_currency(self):
        """Auto-set currency from partner, then refresh rate."""
        if self.partner_id:
            partner = self.partner_id.commercial_partner_id
            partner_currency = (
                partner.property_purchase_currency_id
                if hasattr(partner, 'property_purchase_currency_id')
                and partner.property_purchase_currency_id
                else None
            )
            if not partner_currency and partner.currency_id:
                partner_currency = partner.currency_id
            if partner_currency and partner_currency != self.currency_id:
                self.currency_id = partner_currency
                self._onchange_currency_id_rate()
        else:
            self.currency_id = self.company_id.currency_id
            self.manual_currency_exchange_rate = 1.0

    @api.onchange('currency_id')
    def _onchange_currency_id_rate(self):
        """Auto-fill rate as: 1 [payment_currency] = ? [company_currency]."""
        company_currency = self.company_id.currency_id
        if self.currency_id and self.currency_id != company_currency:
            rate = self.env['res.currency']._get_conversion_rate(
                self.currency_id,
                company_currency,
                self.company_id,
                self.date or fields.Date.today(),
            )
            self.manual_currency_exchange_rate = rate if rate else 1.0
        else:
            self.manual_currency_exchange_rate = 1.0






# # -*- coding: utf-8 -*-
#
# from odoo import api, fields, models
#
#
# class AccountPayment(models.Model):
#     _inherit = 'account.payment'
#
#     # Add new memo field
#     memo_new = fields.Text(
#         string='Memo',
#         help='Additional memo or notes for this payment'
#     )
#
#     # Add advance payment checkbox
#     is_advance_payment = fields.Boolean(
#         string='Advance Payment',
#         default=False,
#         help='Check this box if this is an advance payment'
#     )
#
#     @api.onchange('partner_id')
#     def _onchange_partner_id_currency(self):
#         """
#         When a vendor/customer is selected, automatically set the currency
#         to the partner's assigned currency (property_purchase_currency_id or
#         property_account_receivable currency). Falls back to company currency
#         if the partner has no specific currency assigned.
#         """
#         if self.partner_id:
#             partner = self.partner_id.commercial_partner_id
#
#             # Check if the partner has an explicitly set currency
#             # (set via partner form's Sales & Purchase tab)
#             partner_currency = partner.property_purchase_currency_id \
#                 if hasattr(partner, 'property_purchase_currency_id') \
#                 and partner.property_purchase_currency_id \
#                 else None
#
#             # Fallback: use the currency directly on the partner record
#             if not partner_currency and partner.currency_id:
#                 partner_currency = partner.currency_id
#
#             if partner_currency and partner_currency != self.currency_id:
#                 self.currency_id = partner_currency
#         else:
#             # No partner selected: revert to company currency
#             self.currency_id = self.company_id.currency_id
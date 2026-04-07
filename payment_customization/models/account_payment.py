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

    # Manual currency exchange rate
    manual_currency_exchange_rate = fields.Float(
        string='Exchange Rate',
        digits=(12, 6),
        default=1.0,
        help='Manual exchange rate to use for this payment'
    )

    active_manual_currency_rate = fields.Boolean(
        string='Use Manual Rate',
        default=False,
        help='Enable to set a manual exchange rate for this payment'
    )

    @api.onchange('partner_id')
    def _onchange_partner_id_currency(self):
        """
        When a vendor/customer is selected, automatically set the currency
        to the partner's assigned currency (property_purchase_currency_id or
        property_account_receivable currency). Falls back to company currency
        if the partner has no specific currency assigned.
        """
        if self.partner_id:
            partner = self.partner_id.commercial_partner_id

            # Check if the partner has an explicitly set currency
            partner_currency = partner.property_purchase_currency_id \
                if hasattr(partner, 'property_purchase_currency_id') \
                and partner.property_purchase_currency_id \
                else None

            # Fallback: use the currency directly on the partner record
            if not partner_currency and partner.currency_id:
                partner_currency = partner.currency_id

            if partner_currency and partner_currency != self.currency_id:
                self.currency_id = partner_currency
                self._onchange_currency_id_rate()
        else:
            # No partner selected: revert to company currency
            self.currency_id = self.company_id.currency_id
            self.manual_currency_exchange_rate = 1.0

    @api.onchange('currency_id')
    def _onchange_currency_id_rate(self):
        """Auto-fill the manual rate from the current rate when currency changes."""
        company_currency = self.company_id.currency_id
        if self.currency_id and self.currency_id != company_currency:
            rate = self.env['res.currency']._get_conversion_rate(
                company_currency,
                self.currency_id,
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
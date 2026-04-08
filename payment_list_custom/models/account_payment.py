# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    # Computed amount in company currency using the MANUAL exchange rate.
    #
    # Formula:
    #   amount_manual_company_currency = payment.amount * manual_currency_exchange_rate
    #
    # When payment currency == company currency → manual_currency_exchange_rate = 1.0
    # so the result equals payment.amount (correct, no conversion needed).
    #
    # This replaces amount_company_currency_signed in the list view so that
    # the Amount column always reflects what the user manually entered as the rate,
    # not the system's currency rate table.
    #
    # Sign convention: outbound (vendor) payments are shown negative to match
    # the original amount_company_currency_signed behaviour in the list.

    amount_manual_company_currency = fields.Monetary(
        string='Amount',
        currency_field='company_currency_id',
        compute='_compute_amount_manual_company_currency',
        store=True,
    )

    @api.depends('amount', 'manual_currency_exchange_rate', 'payment_type', 'company_id')
    def _compute_amount_manual_company_currency(self):
        for payment in self:
            rate = payment.manual_currency_exchange_rate or 1.0
            converted = payment.amount * rate
            # Outbound payments (vendor) carry a negative sign in list views
            # to match Odoo's standard amount_company_currency_signed behaviour
            if payment.payment_type == 'outbound':
                converted = -converted
            payment.amount_manual_company_currency = converted

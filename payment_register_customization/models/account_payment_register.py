# -*- coding: utf-8 -*-

from odoo import api, fields, models


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    # ── Existing custom field ──────────────────────────────────────────────────
    memo_new = fields.Text(
        string='Memo',
        help='Additional memo or notes for this payment'
    )

    # ── Company currency (for comparison in view) ──────────────────────────────
    company_currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        string='Company Currency',
        store=False,
    )

    # ── Manual exchange rate ───────────────────────────────────────────────────
    manual_currency_exchange_rate = fields.Float(
        string='Exchange Rate',
        digits=(12, 6),
        default=1.0,
        help='Rate: 1 [payment currency] = ? [company currency]'
    )

    # ── Currency name helpers for the "1 USD = X SAR" label ───────────────────
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

    @api.onchange('currency_id', 'payment_date')
    def _onchange_currency_id_rate(self):
        """Auto-fill rate as: 1 [payment_currency] = ? [company_currency]."""
        company_currency = self.company_id.currency_id
        if self.currency_id and self.currency_id != company_currency:
            rate = self.env['res.currency']._get_conversion_rate(
                self.currency_id,
                company_currency,
                self.company_id,
                self.payment_date or fields.Date.today(),
            )
            self.manual_currency_exchange_rate = rate if rate else 1.0
        else:
            self.manual_currency_exchange_rate = 1.0

    # ── Payment-value overrides ────────────────────────────────────────────────

    def _create_payment_vals_from_wizard(self, batch_result):
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)
        if self.memo_new:
            payment_vals['memo_new'] = self.memo_new
        if self._should_apply_custom_rate():
            payment_vals = self._apply_custom_rate(payment_vals)
        return payment_vals

    def _create_payment_vals_from_batch(self, batch_result):
        payment_vals = super()._create_payment_vals_from_batch(batch_result)
        if self.memo_new:
            payment_vals['memo_new'] = self.memo_new
        if self._should_apply_custom_rate():
            payment_vals = self._apply_custom_rate(payment_vals)
        return payment_vals

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _should_apply_custom_rate(self):
        return (
            self.currency_id
            and self.currency_id != self.company_id.currency_id
            and self.manual_currency_exchange_rate
            and self.manual_currency_exchange_rate != 1.0
        )

    def _apply_custom_rate(self, payment_vals):
        """
        Recalculate debit/credit on every move-line using the manual rate.
        amount_currency (invoice currency) stays untouched;
        only the company-currency columns are recomputed.
        """
        rate = self.manual_currency_exchange_rate

        for cmd in payment_vals.get('line_ids', []):
            if isinstance(cmd, (list, tuple)) and len(cmd) == 3 and isinstance(cmd[2], dict):
                _patch_line(cmd[2], rate)

        for line_vals in payment_vals.get('write_off_line_vals', []):
            if isinstance(line_vals, dict):
                _patch_line(line_vals, rate)

        return payment_vals


# ── Module-level helper ────────────────────────────────────────────────────────

def _patch_line(line_vals, rate):
    """Recalculate debit/credit from amount_currency using the given rate."""
    amount_currency = line_vals.get('amount_currency')
    if amount_currency is None:
        return
    converted = abs(amount_currency) * rate
    if amount_currency >= 0:
        line_vals['debit'] = converted
        line_vals['credit'] = 0.0
    else:
        line_vals['debit'] = 0.0
        line_vals['credit'] = converted











# # -*- coding: utf-8 -*-
#
# from odoo import fields, models
#
#
# class AccountPaymentRegister(models.TransientModel):
#     _inherit = 'account.payment.register'
#
#     # Add new memo field
#     memo_new = fields.Text(
#         string='Memo',
#         help='Additional memo or notes for this payment'
#     )
#
#     def _create_payment_vals_from_wizard(self, batch_result):
#         """Override to include memo_new field when creating payment"""
#         payment_vals = super()._create_payment_vals_from_wizard(batch_result)
#
#         # Add the new memo field to payment values
#         if self.memo_new:
#             payment_vals['memo_new'] = self.memo_new
#
#         return payment_vals
#
#     def _create_payment_vals_from_batch(self, batch_result):
#         """Override to include memo_new field when creating payment from batch"""
#         payment_vals = super()._create_payment_vals_from_batch(batch_result)
#
#         # Add the new memo field to payment values
#         if self.memo_new:
#             payment_vals['memo_new'] = self.memo_new
#
#         return payment_vals
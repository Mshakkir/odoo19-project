# -*- coding: utf-8 -*-
from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Warehouse',
        compute='_compute_analytic_account_id',
        store=True,
    )

    invoice_date_formatted = fields.Char(
        string='Invoice Date',
        compute='_compute_formatted_dates',
        store=False,
    )

    invoice_date_due_formatted = fields.Char(
        string='Due Date',
        compute='_compute_formatted_dates',
        store=False,
    )

    # ── Company Currency Amount Fields ───────────────────────────────────────
    company_currency_id = fields.Many2one(
        related='company_id.currency_id',
        string='Company Currency',
        store=False,
        readonly=True,
    )

    amount_untaxed_company_currency = fields.Monetary(
        string='Tax Excluded (Company Currency)',
        compute='_compute_amounts_company_currency',
        store=True,
        currency_field='company_currency_id',
    )

    amount_tax_company_currency = fields.Monetary(
        string='Tax (Company Currency)',
        compute='_compute_amounts_company_currency',
        store=True,
        currency_field='company_currency_id',
    )

    amount_residual_company_currency = fields.Monetary(
        string='Amount Due (Company Currency)',
        compute='_compute_amounts_company_currency',
        store=True,
        currency_field='company_currency_id',
    )

    @api.depends(
        'amount_untaxed', 'amount_tax', 'amount_residual',
        'manual_currency_rate', 'currency_id', 'company_id'
    )
    def _compute_amounts_company_currency(self):
        for move in self:
            company_currency = move.company_id.currency_id
            inv_currency = move.currency_id
            if inv_currency and company_currency and inv_currency != company_currency:
                rate = move.manual_currency_rate
                if not rate:
                    rate_date = move.invoice_date or fields.Date.today()
                    rate_record = move.env['res.currency.rate'].search([
                        ('currency_id', '=', inv_currency.id),
                        ('company_id', '=', move.company_id.id),
                        ('name', '<=', str(rate_date)),
                    ], order='name desc', limit=1)
                    rate = rate_record.inverse_company_rate if rate_record else 1.0
                move.amount_untaxed_company_currency = move.amount_untaxed * rate
                move.amount_tax_company_currency = move.amount_tax * rate
                move.amount_residual_company_currency = move.amount_residual * rate
            else:
                move.amount_untaxed_company_currency = move.amount_untaxed
                move.amount_tax_company_currency = move.amount_tax
                move.amount_residual_company_currency = move.amount_residual

    @api.depends('invoice_date', 'invoice_date_due')
    def _compute_formatted_dates(self):
        for move in self:
            move.invoice_date_formatted = (
                move.invoice_date.strftime('%d/%m/%Y')
                if move.invoice_date else ''
            )
            move.invoice_date_due_formatted = (
                move.invoice_date_due.strftime('%d/%m/%Y')
                if move.invoice_date_due else ''
            )

    @api.depends('invoice_line_ids', 'invoice_line_ids.analytic_distribution')
    def _compute_analytic_account_id(self):
        for move in self:
            analytic_account_id = False
            if move.invoice_line_ids:
                for line in move.invoice_line_ids:
                    if line.analytic_distribution:
                        account_ids = list(line.analytic_distribution.keys())
                        if account_ids:
                            try:
                                analytic_account_id = int(account_ids[0])
                                break
                            except (ValueError, TypeError):
                                continue
            move.analytic_account_id = analytic_account_id if analytic_account_id else False

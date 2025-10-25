# -*- coding: utf-8 -*-
from odoo import models, fields, api

class AccountAccount(models.Model):
    _inherit = 'account.account'

    debit_amount = fields.Monetary(
        string='Debit',
        compute='_compute_balance_amount',
        currency_field='company_currency_id',
    )
    credit_amount = fields.Monetary(
        string='Credit',
        compute='_compute_balance_amount',
        currency_field='company_currency_id',
    )
    balance_amount = fields.Monetary(
        string='Balance',
        compute='_compute_balance_amount',
        currency_field='company_currency_id',
    )

    @api.depends_context('date_from', 'date_to', 'company_id')
    def _compute_balance_amount(self):
        """Compute balance, debit, and credit for the selected date range."""
        MoveLine = self.env['account.move.line']
        for account in self:
            domain = [
                ('account_id', '=', account.id),
                ('company_id', '=', self.env.context.get('company_id', self.env.company.id))
            ]
            date_from = self.env.context.get('date_from')
            date_to = self.env.context.get('date_to')
            if date_from:
                domain.append(('date', '>=', date_from))
            if date_to:
                domain.append(('date', '<=', date_to))

            data = MoveLine.read_group(domain, ['debit:sum', 'credit:sum'], [])
            debit = data[0]['debit'] if data else 0.0
            credit = data[0]['credit'] if data else 0.0
            account.debit_amount = debit
            account.credit_amount = credit
            account.balance_amount = debit - credit

    def action_view_ledger(self):
        """Open General Ledger lines filtered by this account."""
        self.ensure_one()
        date_from = self.env.context.get('date_from')
        date_to = self.env.context.get('date_to')

        domain = [('account_id', '=', self.id)]
        if date_from:
            domain.append(('date', '>=', date_from))
        if date_to:
            domain.append(('date', '<=', date_to))

        return {
            'name': f'Ledger Entries - {self.code} {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'list,form',
            'domain': domain,
            'context': {'search_default_posted': 1},
            'target': 'current',
        }

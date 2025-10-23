# -*- coding: utf-8 -*-
from odoo import models, fields, api


class AccountAccount(models.Model):
    _inherit = 'account.account'

    balance_amount = fields.Monetary(
        string='Balance',
        compute='_compute_balance_amount',
        currency_field='company_currency_id',
    )

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

    @api.depends_context('date_from', 'date_to', 'company_id')
    def _compute_balance_amount(self):
        """Compute balance, debit, and credit for date range from context"""
        date_from = self.env.context.get('date_from')
        date_to = self.env.context.get('date_to')
        company_id = self.env.context.get('company_id', self.env.company.id)

        for account in self:
            domain = [
                ('account_id', '=', account.id),
                ('company_id', '=', company_id),
            ]

            if date_from:
                domain.append(('date', '>=', date_from))
            if date_to:
                domain.append(('date', '<=', date_to))

            # Get move lines
            move_lines = self.env['account.move.line'].search(domain)

            account.debit_amount = sum(move_lines.mapped('debit'))
            account.credit_amount = sum(move_lines.mapped('credit'))
            account.balance_amount = account.debit_amount - account.credit_amount

    def action_view_ledger(self):
        """Open general ledger for this account"""
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
            'context': {
                'search_default_posted': 1,
                'date_from': date_from,
                'date_to': date_to,
            },
            'target': 'current',
        }
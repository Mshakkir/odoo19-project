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

    @api.depends_context('date_from', 'date_to', 'company_id', 'analytic_account_id')
    def _compute_balance_amount(self):
        """Compute balance, debit, and credit for the selected date range and optional analytic account."""
        MoveLine = self.env['account.move.line']
        for account in self:
            domain = [
                ('account_id', '=', account.id),
                ('company_id', '=', self.env.context.get('company_id', self.env.company.id))
            ]
            date_from = self.env.context.get('date_from')
            date_to = self.env.context.get('date_to')
            analytic_id = self.env.context.get('analytic_account_id')

            if date_from:
                domain.append(('date', '>=', date_from))
            if date_to:
                domain.append(('date', '<=', date_to))
            if analytic_id:
                # If analytic distribution used, we only filter by simple analytic_account_id.
                domain.append(('analytic_account_id', '=', analytic_id))

            # Aggregate values
            # Use read_group for efficient sum
            data = MoveLine.search(domain)
            if data:
                grouped = MoveLine.read_group(domain, ['debit:sum', 'credit:sum'], [])
                data_dict = grouped[0] if grouped else {'debit': 0.0, 'credit': 0.0}
            else:
                data_dict = {'debit': 0.0, 'credit': 0.0}

            debit = data_dict.get('debit', 0.0)
            credit = data_dict.get('credit', 0.0)
            account.debit_amount = debit
            account.credit_amount = credit
            account.balance_amount = debit - credit

    def action_view_ledger(self):
        """Open General Ledger lines filtered by this account and optional wizard context (date_from/date_to/analytic)."""
        self.ensure_one()
        date_from = self.env.context.get('date_from')
        date_to = self.env.context.get('date_to')
        analytic_id = self.env.context.get('analytic_account_id')

        domain = [('account_id', '=', self.id)]
        if date_from:
            domain.append(('date', '>=', date_from))
        if date_to:
            domain.append(('date', '<=', date_to))
        if analytic_id:
            domain.append(('analytic_account_id', '=', analytic_id))

        return {
            'name': f'Ledger Entries - {self.code} {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'list,form',
            'domain': domain,
            'context': {'search_default_posted': 1},
            'target': 'current',
        }














# # -*- coding: utf-8 -*-
# from odoo import models, fields, api
#
#
# class AccountAccount(models.Model):
#     _inherit = 'account.account'
#
#     debit_amount = fields.Monetary(
#         string='Debit',
#         compute='_compute_balance_amount',
#         currency_field='company_currency_id',
#     )
#     credit_amount = fields.Monetary(
#         string='Credit',
#         compute='_compute_balance_amount',
#         currency_field='company_currency_id',
#     )
#     balance_amount = fields.Monetary(
#         string='Balance',
#         compute='_compute_balance_amount',
#         currency_field='company_currency_id',
#     )
#
#     @api.depends_context('date_from', 'date_to', 'company_id')
#     def _compute_balance_amount(self):
#         """Compute balance, debit, and credit for the selected date range."""
#         MoveLine = self.env['account.move.line']
#         for account in self:
#             domain = [
#                 ('account_id', '=', account.id),
#                 ('company_id', '=', self.env.context.get('company_id', self.env.company.id))
#             ]
#             date_from = self.env.context.get('date_from')
#             date_to = self.env.context.get('date_to')
#             if date_from:
#                 domain.append(('date', '>=', date_from))
#             if date_to:
#                 domain.append(('date', '<=', date_to))
#
#             # Aggregate values
#             data = MoveLine.read_group(
#                 domain,
#                 ['debit:sum', 'credit:sum'],
#                 []
#             )[0] if MoveLine.search(domain, limit=1) else {'debit': 0.0, 'credit': 0.0}
#
#             debit = data.get('debit', 0.0)
#             credit = data.get('credit', 0.0)
#             account.debit_amount = debit
#             account.credit_amount = credit
#             account.balance_amount = debit - credit
#
#     def action_view_ledger(self):
#         """Open General Ledger lines filtered by this account."""
#         self.ensure_one()
#         date_from = self.env.context.get('date_from')
#         date_to = self.env.context.get('date_to')
#
#         domain = [('account_id', '=', self.id)]
#         if date_from:
#             domain.append(('date', '>=', date_from))
#         if date_to:
#             domain.append(('date', '<=', date_to))
#
#         return {
#             'name': f'Ledger Entries - {self.code} {self.name}',
#             'type': 'ir.actions.act_window',
#             'res_model': 'account.move.line',
#             'view_mode': 'list,form',
#             'domain': domain,
#             'context': {'search_default_posted': 1},
#             'target': 'current',
#         }
#
#
#
#
#
#

# -*- coding: utf-8 -*-
from odoo import models, api


class AccountingReport(models.TransientModel):
    _inherit = 'accounting.report'

    def action_view_balance_sheet_details(self):
        self.ensure_one()

        lines = self._get_balance_sheet_lines()

        self.env['custom.balance.sheet.line'].search([]).unlink()

        for line in lines:
            self.env['custom.balance.sheet.line'].create({
                'name': line.get('name') or 'Unnamed Account',
                'account_type': line.get('account_type'),
                'debit': line.get('debit', 0.0),
                'credit': line.get('credit', 0.0),
                'balance': line.get('balance', 0.0),
                'currency_id': self.env.company.currency_id.id,
            })

        return {
            'name': 'Balance Sheet Details',
            'type': 'ir.actions.act_window',
            'res_model': 'custom.balance.sheet.line',
            'view_mode': 'list',
            'views': [(self.env.ref('custom_bs_pl_module.view_account_list_balance_sheet').id, 'tree')],
            'target': 'current',
        }

    def _get_balance_sheet_lines(self):
        """Compute account balances for the company"""
        query = """
               SELECT 
                   aa.id AS account_id,
                   aa.name AS account_name,
                   aa.account_type AS account_type,
                   SUM(aml.debit) AS debit,
                   SUM(aml.credit) AS credit,
                   SUM(aml.debit - aml.credit) AS balance
               FROM account_move_line aml
               JOIN account_account aa ON aml.account_id = aa.id
               WHERE aml.company_id = %s
               GROUP BY aa.id, aa.name, aa.account_type
               ORDER BY aa.account_type, aa.name
           """
        self.env.cr.execute(query, [self.env.company.id])
        result = self.env.cr.dictfetchall()
        return result

    def action_view_profit_loss_details(self):
        """Open the Profit & Loss detail list."""
        self.ensure_one()

        pl_types = ['income', 'income_other', 'expense', 'expense_depreciation', 'expense_direct_cost']
        accounts = self.env['account.account'].search([('account_type', 'in', pl_types)])

        return {
            'name': 'Profit & Loss Details',
            'type': 'ir.actions.act_window',
            'res_model': 'account.account',
            'view_mode': 'list',
            'views': [(self.env.ref('custom_bs_pl_module.view_account_list_profit_loss').id, 'list')],
            'domain': [('id', 'in', accounts.ids)],
            'context': {
                'date_from': self.date_from,
                'date_to': self.date_to,
                'company_id': self.company_id.id,
            },
            'target': 'current',
        }

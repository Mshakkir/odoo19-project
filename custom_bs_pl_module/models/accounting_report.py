# -*- coding: utf-8 -*-
from odoo import models, fields, api


class AccountingReport(models.TransientModel):
    _inherit = 'accounting.report'

    def action_view_balance_sheet_details(self):
        """Open detailed view of Balance Sheet accounts"""
        self.ensure_one()

        # Get all balance sheet account types
        balance_sheet_types = [
            'asset_receivable',
            'asset_cash',
            'asset_current',
            'asset_non_current',
            'asset_prepayments',
            'asset_fixed',
            'liability_payable',
            'liability_credit_card',
            'liability_current',
            'liability_non_current',
            'equity',
            'equity_unaffected',
        ]

        # Get accounts with these types
        accounts = self.env['account.account'].search([
            ('account_type', 'in', balance_sheet_types),
            ('company_id', '=', self.company_id.id),
        ])

        return {
            'name': 'Balance Sheet Account Details',
            'type': 'ir.actions.act_window',
            'res_model': 'account.account',
            'view_mode': 'tree,form',
            'views': [
                (self.env.ref('your_custom_module.view_account_list_balance_sheet').id, 'tree'),
                (False, 'form')
            ],
            'domain': [('id', 'in', accounts.ids)],
            'context': {
                'date_from': self.date_from,
                'date_to': self.date_to,
                'company_id': self.company_id.id,
                'strict_range': self.date_from and self.date_to,
            },
            'target': 'current',
        }

    def action_view_profit_loss_details(self):
        """Open detailed view of Profit & Loss accounts"""
        self.ensure_one()

        # Get all P&L account types
        pl_types = [
            'income',
            'income_other',
            'expense',
            'expense_depreciation',
            'expense_direct_cost',
        ]

        # Get accounts with these types
        accounts = self.env['account.account'].search([
            ('account_type', 'in', pl_types),
            ('company_id', '=', self.company_id.id),
        ])

        return {
            'name': 'Profit & Loss Account Details',
            'type': 'ir.actions.act_window',
            'res_model': 'account.account',
            'view_mode': 'list,form',
            'views': [
                (self.env.ref('your_custom_module.view_account_list_profit_loss').id, 'tree'),
                (False, 'form')
            ],
            'domain': [('id', 'in', accounts.ids)],
            'context': {
                'date_from': self.date_from,
                'date_to': self.date_to,
                'company_id': self.company_id.id,
                'strict_range': self.date_from and self.date_to,
            },
            'target': 'current',
        }
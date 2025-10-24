# -*- coding: utf-8 -*-
from odoo import models, api


class AccountingReport(models.TransientModel):
    _inherit = 'accounting.report'

    @api.model
    def action_view_balance_sheet_details(self):
        # 1. Get computed report lines (with debit, credit, balance)
        lines = self._get_balance_sheet_lines()

        # 2. Remove previous transient data
        self.env['custom.balance.sheet.line'].search([]).unlink()

        # 3. Insert new data rows for the window view
        for line in lines:
            self.env['custom.balance.sheet.line'].create({
                'name': line.get('name'),
                'account_type': line.get('account_type'),
                'debit': line.get('debit', 0.0),
                'credit': line.get('credit', 0.0),
                'balance': line.get('balance', 0.0),
                'currency_id': self.env.company.currency_id.id,
            })

        # 4. Return a window action showing the new transient data
        return {
            'name': 'Balance Sheet Details',
            'type': 'ir.actions.act_window',
            'res_model': 'custom.balance.sheet.line',
            'view_mode': 'tree',
            'views': [(self.env.ref('custom_bs_pl_module.view_account_list_balance_sheet').id, 'tree')],
            'target': 'current',
        }

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







# # -*- coding: utf-8 -*-
# from odoo import models, fields, api
#
#
# class AccountingReport(models.TransientModel):
#     _inherit = 'accounting.report'
#
#     def action_view_balance_sheet_details(self):
#         """Open detailed view of Balance Sheet accounts, excluding VAT accounts from list"""
#         self.ensure_one()
#
#         balance_sheet_types = [
#             'asset_receivable',
#             'asset_cash',
#             'asset_current',
#             'asset_non_current',
#             'asset_prepayments',
#             'asset_fixed',
#             'liability_payable',
#             'liability_credit_card',
#             'liability_current',
#             'liability_non_current',
#             'equity',
#             'equity_unaffected',
#         ]
#
#         # Get accounts for list view, exclude VAT accounts
#         accounts = self.env['account.account'].search([
#             ('account_type', 'in', balance_sheet_types),
#             ('code', 'not in', ['101060', '104041', '201017'])
#         ])
#
#         return {
#             'name': 'Balance Sheet Account Details',
#             'type': 'ir.actions.act_window',
#             'res_model': 'account.account',
#             'view_mode': 'list,form',
#             'views': [
#                 (self.env.ref('custom_bs_pl_module.view_account_list_balance_sheet').id, 'list'),
#                 (False, 'form')
#             ],
#             'domain': [('id', 'in', accounts.ids)],
#             'context': {
#                 'date_from': self.date_from,
#                 'date_to': self.date_to,
#                 'company_id': self.company_id.id,
#                 'strict_range': self.date_from and self.date_to,
#             },
#             'target': 'current',
#         }
#
#     def action_view_profit_loss_details(self):
#         """Open detailed view of Profit & Loss accounts"""
#         self.ensure_one()
#
#         # Get all P&L account types
#         pl_types = [
#             'income',
#             'income_other',
#             'expense',
#             'expense_depreciation',
#             'expense_direct_cost',
#         ]
#
#         # Get accounts with these types
#         accounts = self.env['account.account'].search([
#             ('account_type', 'in', pl_types),
#         ])
#
#         return {
#             'name': 'Profit & Loss Account Details',
#             'type': 'ir.actions.act_window',
#             'res_model': 'account.account',
#             'view_mode': 'list,form',
#             'views': [
#                 (self.env.ref('custom_bs_pl_module.view_account_list_profit_loss').id, 'list'),
#                 (False, 'form')
#             ],
#             'domain': [('id', 'in', accounts.ids)],
#             'context': {
#                 'date_from': self.date_from,
#                 'date_to': self.date_to,
#                 'company_id': self.company_id.id,
#                 'strict_range': self.date_from and self.date_to,
#             },
#             'target': 'current',
#         }
# import time
# from odoo import api, models, _
# from odoo.exceptions import UserError
#
#
# class ReportTrialBalance(models.AbstractModel):
#     _name = 'report.accounting_pdf_reports.report_trialbalance'
#     _description = 'Trial Balance Report'
#
#     def _get_accounts(self, accounts, display_account):
#         """ compute the balance, debit and credit for the provided accounts
#             :Arguments:
#                 `accounts`: list of accounts record,
#                 `display_account`: it's used to display either all accounts or those accounts which balance is > 0
#             :Returns a list of dictionary of Accounts with following key and value
#                 `name`: Account name,
#                 `code`: Account code,
#                 `credit`: total amount of credit,
#                 `debit`: total amount of debit,
#                 `balance`: total amount of balance,
#         """
#
#         account_result = {}
#         # Prepare sql query base on selected parameters from wizard
#         tables, where_clause, where_params = self.env['account.move.line']._query_get()
#         tables = tables.replace('"','')
#         if not tables:
#             tables = 'account_move_line'
#         wheres = [""]
#         if where_clause.strip():
#             wheres.append(where_clause.strip())
#         filters = " AND ".join(wheres)
#         # compute the balance, debit and credit for the provided accounts
#         request = ("SELECT account_id AS id, SUM(debit) AS debit, SUM(credit) AS credit, "
#                    "(SUM(debit) - SUM(credit)) AS balance" +\
#                    " FROM " + tables + " WHERE account_id IN %s " + filters + " GROUP BY account_id")
#         params = (tuple(accounts.ids),) + tuple(where_params)
#         self.env.cr.execute(request, params)
#         for row in self.env.cr.dictfetchall():
#             account_result[row.pop('id')] = row
#
#         account_res = []
#         for account in accounts:
#             res = dict((fn, 0.0) for fn in ['credit', 'debit', 'balance'])
#             currency = account.currency_id and account.currency_id or self.env.company.currency_id
#             res['code'] = account.code
#             res['name'] = account.name
#             if account.id in account_result:
#                 res['debit'] = account_result[account.id].get('debit')
#                 res['credit'] = account_result[account.id].get('credit')
#                 res['balance'] = account_result[account.id].get('balance')
#             if display_account == 'all':
#                 account_res.append(res)
#             if display_account == 'not_zero' and not currency.is_zero(res['balance']):
#                 account_res.append(res)
#             if display_account == 'movement' and (not currency.is_zero(res['debit']) or not currency.is_zero(res['credit'])):
#                 account_res.append(res)
#         return account_res
#
#     @api.model
#     def _get_report_values(self, docids, data=None):
#         if not data.get('form') or not self.env.context.get('active_model'):
#             raise UserError(_("Form content is missing, this report cannot be printed."))
#
#         model = self.env.context.get('active_model')
#         docs = self.env[model].browse(self.env.context.get('active_ids', []))
#         display_account = data['form'].get('display_account')
#         accounts = docs if model == 'account.account' else self.env['account.account'].search([])
#         context = data['form'].get('used_context')
#         analytic_accounts = []
#         if data['form'].get('analytic_account_ids'):
#             analytic_account_ids = self.env['account.analytic.account'].browse(data['form'].get('analytic_account_ids'))
#             context['analytic_account_ids'] = analytic_account_ids
#             analytic_accounts = [account.name for account in analytic_account_ids]
#         account_res = self.with_context(context)._get_accounts(accounts, display_account)
#         codes = []
#         if data['form'].get('journal_ids', False):
#             codes = [journal.code for journal in
#                      self.env['account.journal'].search(
#                          [('id', 'in', data['form']['journal_ids'])])]
#         return {
#             'doc_ids': self.ids,
#             'doc_model': model,
#             'data': data['form'],
#             'docs': docs,
#             'print_journal': codes,
#             'analytic_accounts': analytic_accounts,
#             'time': time,
#             'Accounts': account_res,
#         }
# -*- coding: utf-8 -*-
from odoo import models, api


class ReportTrialBalance(models.AbstractModel):
    _inherit = 'report.om_account_accountant.report_trialbalance'

    # Or it might be: _inherit = 'report.account_trial_balance.report_trialbalance'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Override to include all journals from all companies"""

        # Get the original report values
        res = super(ReportTrialBalance, self)._get_report_values(docids, data)

        # Get all companies (main + branches)
        companies = self.env['res.company'].search([])

        # Get all journals from all companies
        all_journals = self.env['account.journal'].search([
            ('company_id', 'in', companies.ids)
        ])

        # Update the print_journal to include all journals
        res['print_journal'] = all_journals.mapped('name')

        # Get combined account data from all companies
        accounts_data = self._get_accounts_data_multi_company(data, companies)
        res['Accounts'] = accounts_data

        return res

    def _get_accounts_data_multi_company(self, data, companies):
        """Get trial balance data from multiple companies combined"""
        all_accounts = {}

        for company in companies:
            # Switch company context
            company_self = self.with_company(company)

            # Get journals for this company
            journals = self.env['account.journal'].search([
                ('company_id', '=', company.id)
            ])

            # Update data with current company's journals
            company_data = data.copy() if data else {}
            company_data['journal_ids'] = journals.ids

            # Get accounts for this company
            accounts = company_self._get_accounts(company_data)

            # Combine accounts (group by account code)
            for account in accounts:
                account_code = account['code']
                if account_code in all_accounts:
                    # Add to existing account
                    all_accounts[account_code]['debit'] += account['debit']
                    all_accounts[account_code]['credit'] += account['credit']
                    all_accounts[account_code]['balance'] += account['balance']
                else:
                    # New account
                    all_accounts[account_code] = account.copy()

        # Convert back to list and sort by code
        result = sorted(all_accounts.values(), key=lambda x: x['code'])
        return result

    def _get_accounts(self, data):
        """
        This method should already exist in the parent class.
        If it doesn't, you'll need to implement the logic to fetch
        account move lines based on the data dictionary.
        """
        # Call parent method if it exists
        if hasattr(super(ReportTrialBalance, self), '_get_accounts'):
            return super(ReportTrialBalance, self)._get_accounts(data)

        # Otherwise implement your own logic here
        # This is a basic example - adjust based on your actual implementation
        display_account = data.get('display_account', 'movement')
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        target_move = data.get('target_move', 'posted')
        journal_ids = data.get('journal_ids', [])

        domain = [
            ('account_id.account_type', 'not in', ['off_balance']),
        ]

        if journal_ids:
            domain.append(('journal_id', 'in', journal_ids))

        if date_from:
            domain.append(('date', '>=', date_from))

        if date_to:
            domain.append(('date', '<=', date_to))

        if target_move == 'posted':
            domain.append(('move_id.state', '=', 'posted'))

        # Get move lines
        move_lines = self.env['account.move.line'].search(domain)

        # Group by account
        accounts_dict = {}
        for line in move_lines:
            account = line.account_id
            if account.code not in accounts_dict:
                accounts_dict[account.code] = {
                    'code': account.code,
                    'name': account.name,
                    'debit': 0.0,
                    'credit': 0.0,
                    'balance': 0.0,
                }
            accounts_dict[account.code]['debit'] += line.debit
            accounts_dict[account.code]['credit'] += line.credit
            accounts_dict[account.code]['balance'] += line.balance

        # Filter based on display_account
        accounts = list(accounts_dict.values())
        if display_account == 'movement':
            accounts = [a for a in accounts if a['debit'] != 0 or a['credit'] != 0]
        elif display_account == 'not_zero':
            accounts = [a for a in accounts if a['balance'] != 0]

        return accounts


class TrialBalanceWizard(models.TransientModel):
    _inherit = 'account.common.journal.report'

    # Or it might be different - check the actual wizard model name

    def check_report(self):
        """Override to pass all journals to the report"""
        # Get all companies
        companies = self.env['res.company'].search([])

        # Get all journals from all companies
        all_journals = self.env['account.journal'].search([
            ('company_id', 'in', companies.ids)
        ])

        # Prepare data
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': self.read()[0]
        }

        # Override journal_ids to include all journals
        data['form']['journal_ids'] = all_journals.ids

        return self.env.ref('om_account_accountant.action_report_trial_balance').report_action(
            self, data=data
        )
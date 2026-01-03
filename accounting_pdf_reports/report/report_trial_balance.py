# # import time
# # from odoo import api, models, _
# # from odoo.exceptions import UserError
# #
# #
# # class ReportTrialBalance(models.AbstractModel):
# #     _name = 'report.accounting_pdf_reports.report_trialbalance'
# #     _description = 'Trial Balance Report'
# #
# #     def _get_accounts(self, accounts, display_account):
# #         account_result = {}
# #         tables, where_clause, where_params = self.env['account.move.line']._query_get()
# #         tables = tables.replace('"', '')
# #         if not tables:
# #             tables = 'account_move_line'
# #         wheres = [""]
# #
# #         if where_clause.strip():
# #             wheres.append(where_clause.strip())
# #
# #         # # ✅ FIX: Analytic filter using subquery (Odoo 19+ compatible)
# #         # analytic_account_ids = self.env.context.get('analytic_account_ids')
# #         # analytic_filter = ""
# #         # analytic_params = ()
# #         #
# #         # if analytic_account_ids:
# #         #     analytic_filter = (
# #         #         " AND (id IN (SELECT move_id FROM account_analytic_line WHERE account_id IN %s)"
# #         #         " OR id NOT IN (SELECT move_id FROM account_analytic_line))"
# #         #     )
# #         #
# #         #     analytic_params = (tuple(a.id for a in analytic_account_ids),)
# #         #
# #         # filters = " AND ".join(wheres)
# #         #
# #         # # ✅ Safe SQL query
# #         # request = (
# #         #     "SELECT account_id AS id, SUM(debit) AS debit, SUM(credit) AS credit, "
# #         #     "(SUM(debit) - SUM(credit)) AS balance "
# #         #     f"FROM {tables} "
# #         #     "WHERE account_id IN %s " + filters + analytic_filter +
# #         #     " GROUP BY account_id"
# #         # )
# #
# #         # params = (tuple(accounts.ids),) + tuple(where_params) + analytic_params
# #         # self.env.cr.execute(request, params)
# #
# #         for row in self.env.cr.dictfetchall():
# #             account_result[row.pop('id')] = row
# #
# #         # Build result
# #         account_res = []
# #         for account in accounts:
# #             res = dict((fn, 0.0) for fn in ['credit', 'debit', 'balance'])
# #             currency = account.currency_id or self.env.company.currency_id
# #             res['code'] = account.code
# #             res['name'] = account.name
# #
# #             if account.id in account_result:
# #                 res.update(account_result[account.id])
# #
# #             if display_account == 'all':
# #                 account_res.append(res)
# #             elif display_account == 'not_zero' and not currency.is_zero(res['balance']):
# #                 account_res.append(res)
# #             elif display_account == 'movement' and (
# #                 not currency.is_zero(res['debit']) or not currency.is_zero(res['credit'])
# #             ):
# #                 account_res.append(res)
# #
# #         return account_res
# #
# #     @api.model
# #     def _get_report_values(self, docids, data=None):
# #         if not data.get('form') or not self.env.context.get('active_model'):
# #             raise UserError(_("Form content is missing, this report cannot be printed."))
# #
# #         model = self.env.context.get('active_model')
# #         docs = self.env[model].browse(self.env.context.get('active_ids', []))
# #         display_account = data['form'].get('display_account')
# #         accounts = docs if model == 'account.account' else self.env['account.account'].search([])
# #         context = data['form'].get('used_context') or {}
# #
# #         # Handle analytic accounts
# #         analytic_accounts = []
# #         if data['form'].get('analytic_account_ids'):
# #             analytic_account_ids = self.env['account.analytic.account'].browse(
# #                 data['form'].get('analytic_account_ids')
# #             )
# #             context['analytic_account_ids'] = analytic_account_ids
# #             analytic_accounts = [account.name for account in analytic_account_ids]
# #
# #         account_res = self.with_context(context)._get_accounts(accounts, display_account)
# #
# #         return {
# #             'doc_ids': self.ids,
# #             'doc_model': model,
# #             'data': data['form'],
# #             'docs': docs,
# #             'print_journal': [],
# #             'analytic_accounts': analytic_accounts,
# #             'time': time,
# #             'Accounts': account_res,
# #         }
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
#         """
#         Compute the balance, debit, and credit for the provided accounts.
#
#         Args:
#             accounts: recordset of account.account
#             display_account: filter option ('all', 'not_zero', or 'movement')
#
#         Returns:
#             list of dicts containing:
#                 - name: Account name
#                 - code: Account code
#                 - debit: Total debit
#                 - credit: Total credit
#                 - balance: Total balance
#         """
#         account_result = {}
#
#         # Prepare SQL query based on selected parameters from wizard
#         tables, where_clause, where_params = self.env['account.move.line']._query_get()
#         tables = tables.replace('"', '') or 'account_move_line'
#
#         wheres = []
#         if where_clause.strip():
#             wheres.append(where_clause.strip())
#         filters = " AND ".join(wheres)
#
#         # Compute debit, credit, and balance for provided accounts
#         request = (
#             "SELECT account_id AS id, "
#             "SUM(debit) AS debit, "
#             "SUM(credit) AS credit, "
#             "(SUM(debit) - SUM(credit)) AS balance "
#             f"FROM {tables} "
#             "WHERE account_id IN %s "
#             + (f"AND {filters}" if filters else "")
#             + " GROUP BY account_id"
#         )
#
#         params = (tuple(accounts.ids),) + tuple(where_params)
#         self.env.cr.execute(request, params)
#
#         for row in self.env.cr.dictfetchall():
#             account_result[row.pop('id')] = row
#
#         account_res = []
#         for account in accounts:
#             res = dict.fromkeys(['credit', 'debit', 'balance'], 0.0)
#             currency = account.currency_id or self.env.company.currency_id
#
#             res.update({
#                 'code': account.code,
#                 'name': account.name,
#             })
#
#             if account.id in account_result:
#                 res['debit'] = account_result[account.id].get('debit', 0.0)
#                 res['credit'] = account_result[account.id].get('credit', 0.0)
#                 res['balance'] = account_result[account.id].get('balance', 0.0)
#
#             if display_account == 'all':
#                 account_res.append(res)
#             elif display_account == 'not_zero' and not currency.is_zero(res['balance']):
#                 account_res.append(res)
#             elif display_account == 'movement' and (
#                 not currency.is_zero(res['debit']) or not currency.is_zero(res['credit'])
#             ):
#                 account_res.append(res)
#
#         return account_res
#
#     @api.model
#     def _get_report_values(self, docids, data=None):
#         """
#         Build data dictionary for the Trial Balance PDF report.
#         """
#         if not data.get('form') or not self.env.context.get('active_model'):
#             raise UserError(_("Form content is missing, this report cannot be printed."))
#
#         model = self.env.context.get('active_model')
#         docs = self.env[model].browse(self.env.context.get('active_ids', []))
#         display_account = data['form'].get('display_account')
#         context = data['form'].get('used_context', {})
#
#         # Get accounts to display
#         accounts = docs if model == 'account.account' else self.env['account.account'].search([])
#
#         # Handle analytic accounts filter
#         analytic_accounts = []
#         if data['form'].get('analytic_account_ids'):
#             analytic_account_ids = self.env['account.analytic.account'].browse(
#                 data['form'].get('analytic_account_ids')
#             )
#             context['analytic_account_ids'] = analytic_account_ids
#             analytic_accounts = [account.name for account in analytic_account_ids]
#
#         # Get filtered account results
#         account_res = self.with_context(context)._get_accounts(accounts, display_account)
#
#         # Get journal codes for header display
#         codes = []
#         if data['form'].get('journal_ids'):
#             codes = [
#                 journal.code
#                 for journal in self.env['account.journal'].search(
#                     [('id', 'in', data['form']['journal_ids'])]
#                 )
#             ]
#
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
from odoo import models, fields

class TrialBalanceLine(models.TransientModel):
    _name = 'trial.balance.line'
    _description = 'Trial Balance Line'

    wizard_id = fields.Many2one('account.balance.report', string='Wizard')
    account_id = fields.Many2one('account.account', string='Account')
    opening_balance = fields.Monetary(string='Opening Balance', currency_field='company_currency_id')
    debit = fields.Monetary(string='Debit', currency_field='company_currency_id')
    credit = fields.Monetary(string='Credit', currency_field='company_currency_id')
    ending_balance = fields.Monetary(string='Ending Balance', currency_field='company_currency_id')
    company_currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

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
#         Compute debit, credit, and balance for the provided accounts.
#         Optional filtering by analytic accounts if present in context.
#         """
#         account_result = {}
#         tables, where_clause, where_params = self.env['account.move.line']._query_get()
#         tables = tables.replace('"', '')
#         if not tables:
#             tables = 'account_move_line'
#
#         wheres = [""]
#         if where_clause.strip():
#             wheres.append(where_clause.strip())
#         filters = " AND ".join(wheres)
#
#         # --- Analytic account filter (optional) ---
#         analytic_account_ids = self.env.context.get('analytic_account_ids', [])
#         analytic_clause = ""
#         analytic_params = ()
#         if analytic_account_ids:
#             # Ensure we have a list of IDs
#             if not isinstance(analytic_account_ids, list):
#                 analytic_account_ids = [aa.id for aa in analytic_account_ids]
#             analytic_json_list = [f'[{{"account_id": {aa_id}}}]' for aa_id in analytic_account_ids]
#             analytic_clause = " AND (" + " OR ".join(["analytic_distribution::jsonb @> %s"] * len(analytic_json_list)) + ")"
#             analytic_params = tuple(analytic_json_list)
#
#         # --- SQL query ---
#         request = (
#             "SELECT account_id AS id, SUM(debit) AS debit, SUM(credit) AS credit, "
#             "(SUM(debit) - SUM(credit)) AS balance "
#             "FROM " + tables +
#             " WHERE account_id IN %s " + filters + analytic_clause +
#             " GROUP BY account_id"
#         )
#         params = (tuple(accounts.ids),) + tuple(where_params) + analytic_params
#         self.env.cr.execute(request, params)
#         for row in self.env.cr.dictfetchall():
#             account_result[row.pop('id')] = row
#
#         # --- Build account result for QWeb ---
#         account_res = []
#         for account in accounts:
#             res = dict((fn, 0.0) for fn in ['credit', 'debit', 'balance'])
#             currency = account.currency_id or self.env.company.currency_id
#             res['code'] = account.code
#             res['name'] = account.name
#             if account.id in account_result:
#                 res['debit'] = account_result[account.id].get('debit')
#                 res['credit'] = account_result[account.id].get('credit')
#                 res['balance'] = account_result[account.id].get('balance')
#             if display_account == 'all':
#                 account_res.append(res)
#             elif display_account == 'not_zero' and not currency.is_zero(res['balance']):
#                 account_res.append(res)
#             elif display_account == 'movement' and (not currency.is_zero(res['debit']) or not currency.is_zero(res['credit'])):
#                 account_res.append(res)
#         return account_res
#
#     @api.model
#     def _get_report_values(self, docids, data=None):
#         """
#         Prepare report values for Trial Balance QWeb.
#         Supports optional analytic account filtering.
#         """
#         if not data.get('form') or not self.env.context.get('active_model'):
#             raise UserError(_("Form content is missing, this report cannot be printed."))
#
#         model = self.env.context.get('active_model')
#         docs = self.env[model].browse(self.env.context.get('active_ids', []))
#         display_account = data['form'].get('display_account')
#         accounts = docs if model == 'account.account' else self.env['account.account'].search([])
#
#         # --- Optional analytic account context ---
#         context = data['form'].get('used_context') or {}
#         analytic_accounts = []
#         if data['form'].get('analytic_account_ids'):
#             analytic_account_ids = self.env['account.analytic.account'].browse(
#                 data['form'].get('analytic_account_ids', [])
#             )
#             context['analytic_account_ids'] = analytic_account_ids
#             analytic_accounts = [aa.name for aa in analytic_account_ids]
#
#         # --- Compute account balances ---
#         account_res = self.with_context(context)._get_accounts(accounts, display_account)
#
#         # --- Journal codes ---
#         codes = []
#         if data['form'].get('journal_ids'):
#             codes = [journal.code for journal in self.env['account.journal'].browse(data['form']['journal_ids'])]
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
import time
import json
from odoo import api, models, _
from odoo.exceptions import UserError


class ReportTrialBalance(models.AbstractModel):
    _name = 'report.accounting_pdf_reports.report_trialbalance'
    _description = 'Trial Balance Report'

    def _get_accounts(self, accounts, display_account):
        account_result = {}
        tables, where_clause, where_params = self.env['account.move.line']._query_get()
        tables = tables.replace('"', '')
        if not tables:
            tables = 'account_move_line'

        wheres = [""]  # base condition
        if where_clause.strip():
            wheres.append(where_clause.strip())
        filters = " AND ".join(wheres)

        # Build analytic filter (JSONB contains key)
        analytic_account_ids = self.env.context.get('analytic_account_ids', [])
        analytic_clause = ""
        analytic_params = ()
        if analytic_account_ids:
            analytic_ids_str = [str(aid) for aid in analytic_account_ids]
            analytic_clause = " AND (" + " OR ".join(
                ["analytic_distribution::jsonb ? %s"] * len(analytic_ids_str)
            ) + ")"
            analytic_params = tuple(analytic_ids_str)

        # SQL query to aggregate account balances
        request = (
            "SELECT account_id AS id, SUM(debit) AS debit, SUM(credit) AS credit, "
            "(SUM(debit) - SUM(credit)) AS balance "
            "FROM " + tables +
            " WHERE account_id IN %s " + filters + analytic_clause +
            " GROUP BY account_id"
        )
        params = (tuple(accounts.ids),) + tuple(where_params) + analytic_params
        self.env.cr.execute(request, params)
        for row in self.env.cr.dictfetchall():
            account_result[row.pop('id')] = row

        # Prepare output
        account_res = []
        for account in accounts:
            res = dict((fn, 0.0) for fn in ['credit', 'debit', 'balance'])
            currency = account.currency_id or self.env.company.currency_id
            res['code'] = account.code
            res['name'] = account.name
            if account.id in account_result:
                res['debit'] = account_result[account.id].get('debit')
                res['credit'] = account_result[account.id].get('credit')
                res['balance'] = account_result[account.id].get('balance')
            if display_account == 'all':
                account_res.append(res)
            elif display_account == 'not_zero' and not currency.is_zero(res['balance']):
                account_res.append(res)
            elif display_account == 'movement' and (
                not currency.is_zero(res['debit']) or not currency.is_zero(res['credit'])
            ):
                account_res.append(res)
        return account_res

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form') or not self.env.context.get('active_model'):
            raise UserError(_("Form content is missing, this report cannot be printed."))

        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_ids', []))
        display_account = data['form'].get('display_account')
        accounts = docs if model == 'account.account' else self.env['account.account'].search([])

        # Prepare context for analytic filtering
        context = data['form'].get('used_context') or {}
        analytic_accounts = []
        analytic_ids = []
        if data['form'].get('analytic_account_ids'):
            analytic_recs = self.env['account.analytic.account'].browse(
                data['form'].get('analytic_account_ids', [])
            )
            analytic_ids = analytic_recs.ids
            context['analytic_account_ids'] = analytic_ids
            # Handle multilingual JSON names
            for acc in analytic_recs:
                try:
                    name_data = json.loads(acc.name) if acc.name.startswith('{') else acc.name
                    analytic_accounts.append(
                        name_data.get('en_US') if isinstance(name_data, dict) else name_data
                    )
                except Exception:
                    analytic_accounts.append(acc.name)

        # Compute results
        account_res = self.with_context(context)._get_accounts(accounts, display_account)

        # Journal codes
        codes = []
        if data['form'].get('journal_ids'):
            codes = [journal.code for journal in self.env['account.journal'].browse(data['form']['journal_ids'])]

        return {
            'doc_ids': self.ids,
            'doc_model': model,
            'data': data['form'],
            'docs': docs,
            'print_journal': codes,
            'analytic_accounts': analytic_accounts,
            'time': time,
            'Accounts': account_res,
        }


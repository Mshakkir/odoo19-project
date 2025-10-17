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
import time
from odoo import api, models, _
from odoo.exceptions import UserError


class ReportTrialBalance(models.AbstractModel):
    _name = 'report.accounting_pdf_reports.report_trialbalance'
    _description = 'Trial Balance Report'

    # ------------------------------
    # Multi-company aware account fetch
    # ------------------------------
    def _get_accounts(self, accounts, display_account):
        account_result = {}
        tables, where_clause, where_params = self.env['account.move.line']._query_get()

        # Remove double quotes for PostgreSQL compatibility
        tables = tables.replace('"', '') or 'account_move_line'
        wheres = []
        if where_clause.strip():
            wheres.append(where_clause.strip())

        filters = " AND ".join(wheres) if wheres else ""

        # 🔹 Allow multi-company: add an explicit company filter if provided in context
        company_ids = self.env.context.get('allowed_company_ids') or [self.env.company.id]
        company_filter = " AND company_id IN %s"
        filters = (filters + company_filter) if filters else "WHERE company_id IN %s"

        # Compute debit/credit/balance
        request = (
            "SELECT account_id AS id, SUM(debit) AS debit, SUM(credit) AS credit, "
            "(SUM(debit) - SUM(credit)) AS balance "
            f"FROM {tables} WHERE account_id IN %s {filters.replace('WHERE', 'AND', 1)} GROUP BY account_id"
        )

        # Merge parameters (accounts + company + others)
        params = (tuple(accounts.ids), tuple(company_ids)) + tuple(where_params)
        self.env.cr.execute(request, params)

        for row in self.env.cr.dictfetchall():
            account_result[row.pop('id')] = row

        # Prepare results
        account_res = []
        for account in accounts:
            res = dict((fn, 0.0) for fn in ['credit', 'debit', 'balance'])
            currency = account.currency_id or self.env.company.currency_id
            res['code'] = account.code
            res['name'] = account.name
            if account.id in account_result:
                res.update(account_result[account.id])
            if display_account == 'all':
                account_res.append(res)
            elif display_account == 'not_zero' and not currency.is_zero(res['balance']):
                account_res.append(res)
            elif display_account == 'movement' and (
                not currency.is_zero(res['debit']) or not currency.is_zero(res['credit'])
            ):
                account_res.append(res)
        return account_res

    # ------------------------------
    # Pass company context from wizard
    # ------------------------------
    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form') or not self.env.context.get('active_model'):
            raise UserError(_("Form content is missing, this report cannot be printed."))

        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_ids', []))
        display_account = data['form'].get('display_account')

        accounts = docs if model == 'account.account' else self.env['account.account'].search([])

        # 🔹 Capture selected companies from the user/session
        company_ids = self.env.context.get('allowed_company_ids') or [self.env.company.id]

        # Rebuild context for _query_get with our allowed companies
        context = dict(data['form'].get('used_context', {}))
        context['allowed_company_ids'] = company_ids
        context['company_ids'] = company_ids

        analytic_accounts = []
        if data['form'].get('analytic_account_ids'):
            analytic_account_ids = self.env['account.analytic.account'].browse(
                data['form'].get('analytic_account_ids')
            )
            context['analytic_account_ids'] = analytic_account_ids.ids
            analytic_accounts = [acc.name for acc in analytic_account_ids]

        account_res = self.with_context(context)._get_accounts(accounts, display_account)

        codes = []
        if data['form'].get('journal_ids', False):
            codes = [
                journal.code
                for journal in self.env['account.journal'].search(
                    [('id', 'in', data['form']['journal_ids'])]
                )
            ]

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

import time
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
        wheres = [""]

        if where_clause.strip():
            wheres.append(where_clause.strip())

        # 🔹 Analytic filter (Odoo 18/19 compatible)
        analytic_account_ids = self.env.context.get('analytic_account_ids')
        analytic_filter = ""
        analytic_params = ()

        if analytic_account_ids:
            # Use subquery to fetch move_line IDs linked to analytic accounts
            analytic_filter = (
                " AND id IN (SELECT move_id FROM account_analytic_line WHERE account_id IN %s)"
            )
            analytic_params = (tuple(a.id for a in analytic_account_ids),)

        filters = " AND ".join(wheres)

        # 🔹 Build SQL query safely
        request = (
            "SELECT account_id AS id, SUM(debit) AS debit, SUM(credit) AS credit, "
            "(SUM(debit) - SUM(credit)) AS balance "
            f"FROM {tables} "
            "WHERE account_id IN %s " + filters + analytic_filter +
            " GROUP BY account_id"
        )

        params = (tuple(accounts.ids),) + tuple(where_params) + analytic_params
        self.env.cr.execute(request, params)

        for row in self.env.cr.dictfetchall():
            account_result[row.pop('id')] = row

        # 🔹 Build final account result list
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

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form') or not self.env.context.get('active_model'):
            raise UserError(_("Form content is missing, this report cannot be printed."))

        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_ids', []))
        display_account = data['form'].get('display_account')
        accounts = docs if model == 'account.account' else self.env['account.account'].search([])
        context = data['form'].get('used_context') or {}

        # 🔹 Handle analytic accounts from form
        analytic_accounts = []
        if data['form'].get('analytic_account_ids'):
            analytic_account_ids = self.env['account.analytic.account'].browse(data['form'].get('analytic_account_ids'))
            context['analytic_account_ids'] = analytic_account_ids
            analytic_accounts = [account.name for account in analytic_account_ids]

        # 🔹 Generate account results
        account_res = self.with_context(context)._get_accounts(accounts, display_account)

        return {
            'doc_ids': self.ids,
            'doc_model': model,
            'data': data['form'],
            'docs': docs,
            'print_journal': [],
            'analytic_accounts': analytic_accounts,
            'time': time,
            'Accounts': account_res,
        }

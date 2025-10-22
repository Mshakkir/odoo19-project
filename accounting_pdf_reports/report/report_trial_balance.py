import time
from odoo import api, models, _
from odoo.exceptions import UserError


class ReportTrialBalance(models.AbstractModel):
    _name = 'report.accounting_pdf_reports.report_trialbalance'
    _description = 'Trial Balance Report'

    def _get_accounts(self, accounts, display_account):
        account_result = {}

        # Use query_get but remove analytic context to avoid invalid join
        ctx = dict(self.env.context)
        ctx.pop('analytic_account_ids', None)
        tables, where_clause, where_params = self.env['account.move.line'].with_context(ctx)._query_get()

        # Prepare table name
        tables = tables.replace('"', '')
        if not tables:
            tables = 'account_move_line'

        wheres = [""]
        if where_clause.strip():
            wheres.append(where_clause.strip())

        filters = " AND ".join(wheres)

        # 🔹 Analytic account filter (custom subquery instead of column)
        # analytic_account_ids = self.env.context.get('analytic_account_ids')
        # analytic_filter = ""
        # if analytic_account_ids:
        #     analytic_filter = (
        #         " AND account_move_line.id IN ("
        #         "SELECT move_line_id FROM account_analytic_line "
        #         "WHERE account_id IN %s)"
        #     )
        #     where_params = tuple(where_params) + (tuple(a.id for a in analytic_account_ids),)
        analytic_account_ids = self.env.context.get('analytic_account_ids')
        analytic_filter = ""
        if analytic_account_ids:
            analytic_filter = (
                " AND account_move_line.id IN ("
                "SELECT move_line_id FROM account_analytic_line "
                "WHERE account_id IN %s)"
            )
            where_params = tuple(where_params) + (tuple(a.id for a in analytic_account_ids),)

        # 🔹 Build final SQL query
        request = (
            "SELECT account_id AS id, "
            "SUM(debit) AS debit, "
            "SUM(credit) AS credit, "
            "(SUM(debit) - SUM(credit)) AS balance "
            f"FROM {tables} "
            "WHERE account_id IN %s " + filters + analytic_filter +
            " GROUP BY account_id"
        )

        params = (tuple(accounts.ids),) + tuple(where_params)

        # Execute safely
        self.env.cr.execute(request, params)
        for row in self.env.cr.dictfetchall():
            account_result[row.pop('id')] = row

        # 🔹 Process results
        account_res = []
        for account in accounts:
            res = {'code': account.code, 'name': account.name, 'debit': 0.0, 'credit': 0.0, 'balance': 0.0}
            currency = account.currency_id or self.env.company.currency_id

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

        # 🔹 Capture analytic account selection
        analytic_accounts = []
        if data['form'].get('analytic_account_ids'):
            analytic_account_ids = self.env['account.analytic.account'].browse(
                data['form']['analytic_account_ids']
            )
            context['analytic_account_ids'] = analytic_account_ids
            analytic_accounts = [acc.name for acc in analytic_account_ids]

        # 🔹 Fetch account balances with custom context
        account_res = self.with_context(context)._get_accounts(accounts, display_account)

        # 🔹 Fetch selected journal codes
        codes = []
        if data['form'].get('journal_ids', False):
            codes = [
                journal.code
                for journal in self.env['account.journal'].browse(data['form']['journal_ids'])
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

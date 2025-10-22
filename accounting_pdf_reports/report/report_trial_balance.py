import time
from odoo import api, models, _
from odoo.exceptions import UserError


class ReportTrialBalance(models.AbstractModel):
    _name = 'report.accounting_pdf_reports.report_trialbalance'
    _description = 'Trial Balance Report'

    def _get_accounts(self, accounts, display_account):
        account_result = {}

        # Build base query using Odoo ORM helpers
        tables, where_clause, where_params = self.env['account.move.line']._query_get()
        tables = tables.replace('"', '')
        if not tables:
            tables = 'account_move_line'

        wheres = [""]
        if where_clause.strip():
            wheres.append(where_clause.strip())

        filters = " AND ".join(wheres)

        # 🔹 Analytic account filter (use subquery on account_analytic_line)
        analytic_account_ids = self.env.context.get('analytic_account_ids')
        analytic_filter = ""
        if analytic_account_ids:
            analytic_filter = (
                " AND account_move_line.id IN ("
                "SELECT move_line_id FROM account_analytic_line "
                "WHERE account_id IN %s)"
            )
            where_params = tuple(where_params) + (tuple(a.id for a in analytic_account_ids),)

        # Build final query
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

        self.env.cr.execute(request, params)
        for row in self.env.cr.dictfetchall():
            account_result[row.pop('id')] = row

        # Process data for report
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
        context = data['form'].get('used_context')

        # Add analytic accounts (for warehouse-based reporting)
        analytic_accounts = []
        if data['form'].get('analytic_account_ids'):
            analytic_account_ids = self.env['account.analytic.account'].browse(
                data['form'].get('analytic_account_ids')
            )
            context['analytic_account_ids'] = analytic_account_ids
            analytic_accounts = [account.name for account in analytic_account_ids]

        # Fetch account balances
        account_res = self.with_context(context)._get_accounts(accounts, display_account)

        # Journal codes
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

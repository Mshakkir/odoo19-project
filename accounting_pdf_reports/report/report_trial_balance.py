import time
from odoo import api, models, _
from odoo.exceptions import UserError


class ReportTrialBalance(models.AbstractModel):
    _name = 'report.accounting_pdf_reports.report_trialbalance'
    _description = 'Trial Balance Report'

    def _get_accounts(self, accounts, display_account):
        """ compute the balance, debit and credit for the provided accounts """
        account_result = {}
        tables, where_clause, where_params = self.env['account.move.line']._query_get()
        tables = tables.replace('"', '')
        if not tables:
            tables = 'account_move_line'
        wheres = [""]
        if where_clause.strip():
            wheres.append(where_clause.strip())
        filters = " AND ".join(wheres)

        request = ("SELECT account_id AS id, SUM(debit) AS debit, SUM(credit) AS credit, "
                   "(SUM(debit) - SUM(credit)) AS balance"
                   " FROM " + tables + " WHERE account_id IN %s " + filters + " GROUP BY account_id")
        params = (tuple(accounts.ids),) + tuple(where_params)
        self.env.cr.execute(request, params)
        for row in self.env.cr.dictfetchall():
            account_result[row.pop('id')] = row

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
            if display_account == 'not_zero' and not currency.is_zero(res['balance']):
                account_res.append(res)
            if display_account == 'movement' and (not currency.is_zero(res['debit']) or not currency.is_zero(res['credit'])):
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

        # 🔹 Get selected journals from wizard
        journal_ids = data['form'].get('journal_ids', [])
        journals = self.env['account.journal'].browse(journal_ids)

        company_balances = []
        for company in self.env.companies:
            # journals for this company only
            company_journals = journals.filtered(lambda j: j.company_id == company)
            if not company_journals:
                continue

            context = dict(data['form'].get('used_context', {}))
            context.update({
                'allowed_company_ids': [company.id],
                'force_company': company.id,
                'active_test': False,
            })

            account_res = self.with_context(context)._get_accounts(accounts, display_account)
            company_balances.append({
                'company': company,
                'accounts': account_res,
                'journals': company_journals.mapped('code'),
            })

        analytic_accounts = []
        if data['form'].get('analytic_account_ids'):
            analytic_account_ids = self.env['account.analytic.account'].browse(data['form'].get('analytic_account_ids'))
            analytic_accounts = [a.name for a in analytic_account_ids]

        return {
            'doc_ids': self.ids,
            'doc_model': model,
            'data': data['form'],
            'docs': docs,
            'company_balances': company_balances,
            'analytic_accounts': analytic_accounts,
            'time': time,
        }

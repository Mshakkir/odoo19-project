import time
from odoo import api, models, _


class ReportWarehouseTrialBalance(models.AbstractModel):
    _name = 'report.warehouse_financial_reports.warehouse_trial_balance_report'
    _description = 'Warehouse Trial Balance Report'

    def _get_accounts(self, accounts, display_account, analytic_account_ids=None):
        account_result = {}
        tables, where_clause, where_params = self.env['account.move.line']._query_get()
        tables = tables.replace('"', '') or 'account_move_line'
        wheres = [""]
        if where_clause.strip():
            wheres.append(where_clause.strip())

        if analytic_account_ids:
            tables += """ INNER JOIN account_analytic_line aal ON account_move_line.id = aal.move_line_id """
            wheres.append("aal.account_id IN %s")
            where_params += (tuple(analytic_account_ids),)

        filters = " AND ".join(wheres)

        request = (
            "SELECT account_id AS id, SUM(debit) AS debit, SUM(credit) AS credit, "
            "(SUM(debit) - SUM(credit)) AS balance "
            "FROM " + tables + " "
            "WHERE account_id IN %s " + filters + " "
            "GROUP BY account_id"
        )
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
            elif display_account == 'not_zero' and not currency.is_zero(res['balance']):
                account_res.append(res)
            elif display_account == 'movement' and (
                    not currency.is_zero(res['debit']) or not currency.is_zero(res['credit'])
            ):
                account_res.append(res)

        return account_res

    @api.model
    def _get_report_values(self, docids, data=None):
        form_data = data.get('form', data) or {}
        display_account = form_data.get('display_account', 'not_zero')
        accounts = self.env['account.account'].search([])
        context = form_data.get('used_context', {})

        analytic_account_ids = form_data.get('analytic_account_ids', [])
        warehouse_name = form_data.get('warehouse_name', 'All Warehouses')
        report_mode = form_data.get('report_mode', 'consolidated')

        account_res = self.with_context(context)._get_accounts(
            accounts, display_account, analytic_account_ids if report_mode == 'single' else None
        )

        codes = []
        if form_data.get('journal_ids'):
            journals = self.env['account.journal'].browse(form_data['journal_ids'])
            codes = [journal.code for journal in journals if journal.code]

        total_debit = sum(float(acc.get('debit') or 0.0) for acc in account_res)
        total_credit = sum(float(acc.get('credit') or 0.0) for acc in account_res)
        total_balance = sum(float(acc.get('balance') or 0.0) for acc in account_res)

        return {
            'doc_ids': docids,
            'doc_model': 'warehouse.trial.balance',
            'docs': self.env['warehouse.trial.balance'].browse(docids),
            'time': time,
            'Accounts': account_res,
            'print_journal': codes,
            'warehouse_name': warehouse_name,
            'report_mode': report_mode,
            'total_debit': total_debit,
            'total_credit': total_credit,
            'total_balance': total_balance,
            'display_account': display_account,
            'date_from': form_data.get('date_from', False),
            'date_to': form_data.get('date_to', False),
            'target_move': form_data.get('target_move', 'posted'),
        }

import time
from odoo import api, models, _
from odoo.exceptions import UserError

class ReportWarehouseTrialBalance(models.AbstractModel):
    _name = 'report.warehouse_financial_reports.warehouse_trial_balance_report'
    _description = 'Warehouse Trial Balance Report'

    def _get_accounts(self, accounts, display_account, analytic_account_ids=None):
        """
        Compute balance, debit and credit for accounts filtered by warehouse
        """
        account_result = {}

        # Prepare SQL query
        tables, where_clause, where_params = self.env['account.move.line']._query_get()
        tables = tables.replace('"', '')  # remove quotes
        if not tables:
            tables = 'account_move_line'

        wheres = [""]
        if where_clause.strip():
            wheres.append(where_clause.strip())

        # Analytic (warehouse) filter
        if analytic_account_ids:
            tables += """ LEFT JOIN account_analytic_line aal ON account_move_line.id = aal.move_line_id """
            wheres.append("(aal.account_id IN %s OR aal.account_id IS NULL)")
            where_params += (tuple(analytic_account_ids),)

        filters = " AND ".join(wheres)

        # Compute the balance, debit, credit
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
                res['debit'] = float(account_result[account.id].get('debit', 0.0) or 0.0)
                res['credit'] = float(account_result[account.id].get('credit', 0.0) or 0.0)
                res['balance'] = float(account_result[account.id].get('balance', 0.0) or 0.0)

            # Filter accounts
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
        """Generate report values with warehouse filtering"""
        if not data:
            data = {}
        form_data = data.get('form', data)
        if not form_data:
            raise UserError(_("Form content is missing, this report cannot be printed."))

        display_account = form_data.get('display_account')
        accounts = self.env['account.account'].search([])
        context = form_data.get('used_context', {})

        # Analytic (warehouse) filter
        analytic_account_ids = form_data.get('analytic_account_ids', [])
        warehouse_name = form_data.get('warehouse_name', 'All Warehouses')
        report_mode = form_data.get('report_mode', 'consolidated')

        account_res = self.with_context(context)._get_accounts(
            accounts,
            display_account,
            analytic_account_ids if report_mode == 'single' else None
        )

        account_res = account_res or []

        # Get journal codes
        codes = []
        if form_data.get('journal_ids'):
            journals = self.env['account.journal'].browse(form_data['journal_ids'])
            codes = [journal.code for journal in journals if journal.code]

        # Calculate totals
        total_debit = sum(float(acc.get('debit', 0.0) or 0.0) for acc in account_res)
        total_credit = sum(float(acc.get('credit', 0.0) or 0.0) for acc in account_res)
        total_balance = sum(float(acc.get('balance', 0.0) or 0.0) for acc in account_res)

        return {
            'doc_ids': docids,
            'doc_model': 'warehouse.trial.balance',
            'docs': self.env['warehouse.trial.balance'].browse(docids),
            'time': time,
            'Accounts': account_res,
            'print_journal': codes or [],
            'warehouse_name': warehouse_name or 'All Warehouses',
            'report_mode': report_mode or 'consolidated',
            'total_debit': total_debit,
            'total_credit': total_credit,
            'total_balance': total_balance,
            'display_account': form_data.get('display_account', 'not_zero'),
            'date_from': form_data.get('date_from', False),
            'date_to': form_data.get('date_to', False),
            'target_move': form_data.get('target_move', 'posted'),
        }

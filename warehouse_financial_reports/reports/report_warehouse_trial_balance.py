# reports/report_warehouse_trial_balance.py
# ==========================================
import time
from odoo import api, models, _
from odoo.exceptions import UserError


class ReportWarehouseTrialBalance(models.AbstractModel):
    _name = 'report.warehouse_financial_reports.warehouse_trial_balance'
    _description = 'Warehouse Trial Balance Report'

    def _get_accounts(self, accounts, display_account, analytic_account_ids=None):
        """
        Compute balance, debit and credit for accounts filtered by warehouse
        Extended from Odoo Mates to handle single warehouse filtering
        """
        account_result = {}

        # Prepare sql query base on selected parameters
        tables, where_clause, where_params = self.env['account.move.line']._query_get()
        tables = tables.replace('"', '')
        if not tables:
            tables = 'account_move_line'

        wheres = [""]
        if where_clause.strip():
            wheres.append(where_clause.strip())

        # Add analytic account filter for specific warehouse
        if analytic_account_ids:
            # Join with analytic distribution table
            tables += """ 
                LEFT JOIN account_analytic_line aal ON account_move_line.id = aal.move_line_id
            """
            wheres.append("aal.account_id IN %s")
            where_params += (tuple(analytic_account_ids),)

        filters = " AND ".join(wheres)

        # Compute the balance, debit and credit
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

            # Filter based on display_account option
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

    # Handle both old and new data structure
    form_data = data.get('form', data)

    if not form_data:
        raise UserError(_("Form content is missing, this report cannot be printed."))

    display_account = form_data.get('display_account')
    accounts = self.env['account.account'].search([])
    context = form_data.get('used_context', {})

    # Get analytic account (warehouse) information
    analytic_account_ids = form_data.get('analytic_account_ids', [])
    warehouse_name = form_data.get('warehouse_name', 'All Warehouses')
    report_mode = form_data.get('report_mode', 'consolidated')

    # Get accounts with warehouse filtering
    account_res = self.with_context(context)._get_accounts(
        accounts,
        display_account,
        analytic_account_ids if report_mode == 'single' else None
    )

    # Get journal codes
    codes = []
    if form_data.get('journal_ids'):
        codes = [journal.code for journal in
                 self.env['account.journal'].browse(form_data['journal_ids'])]

    # Calculate totals
    total_debit = sum(acc['debit'] for acc in account_res)
    total_credit = sum(acc['credit'] for acc in account_res)
    total_balance = sum(acc['balance'] for acc in account_res)

    return {
        'doc_ids': docids,
        'doc_model': 'warehouse.trial.balance',
        'data': form_data,
        'docs': self.env['warehouse.trial.balance'].browse(docids),
        'time': time,
        'Accounts': account_res,
        'print_journal': codes,
        'warehouse_name': warehouse_name,
        'report_mode': report_mode,
        'total_debit': total_debit,
        'total_credit': total_credit,
        'total_balance': total_balance,
    }

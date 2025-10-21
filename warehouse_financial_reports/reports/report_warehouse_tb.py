# -*- coding: utf-8 -*-
import time
from odoo import api, models


class ReportWarehouseTrialBalance(models.AbstractModel):
    _name = 'report.warehouse_tb'  # short name to avoid PostgreSQL limits
    _description = 'Warehouse Trial Balance Report'

    def _get_accounts(self, accounts, display_account, analytic_account_ids=None):
        account_result = {}

        # Build the SQL query
        tables, where_clause, where_params = self.env['account.move.line']._query_get()
        tables = tables.replace('"', '') or 'account_move_line'
        wheres = ["1=1"]
        if where_clause.strip():
            wheres.append(where_clause.strip())

        if analytic_account_ids:
            tables += " INNER JOIN account_analytic_line aal ON account_move_line.id = aal.move_line_id"
            wheres.append("aal.account_id = ANY(%s)")
            where_params += (analytic_account_ids,)

        filters = " AND ".join(wheres)

        sql = f"""
            SELECT account_id AS id,
                   SUM(debit) AS debit,
                   SUM(credit) AS credit,
                   SUM(debit) - SUM(credit) AS balance
            FROM {tables}
            WHERE account_id = ANY(%s) AND {filters}
            GROUP BY account_id
        """
        params = (accounts.ids,) + tuple(where_params)
        self.env.cr.execute(sql, params)
        for row in self.env.cr.dictfetchall():
            account_result[row.pop('id')] = row

        # Format result for QWeb
        account_res = []
        for account in accounts:
            res = dict((fn, 0.0) for fn in ['debit', 'credit', 'balance'])
            res['code'] = account.code
            res['name'] = account.name
            if account.id in account_result:
                res.update(account_result[account.id])

            if display_account == 'all':
                account_res.append(res)
            elif display_account == 'not_zero' and (res['balance'] != 0):
                account_res.append(res)
            elif display_account == 'movement' and (res['debit'] != 0 or res['credit'] != 0):
                account_res.append(res)
        return account_res

    @api.model
    def _get_report_values(self, docids, data=None):
        form_data = data.get('form', data) or {}
        display_account = form_data.get('display_account', 'not_zero')
        accounts = self.env['account.account'].search([])

        analytic_account_ids = form_data.get('analytic_account_ids', [])
        warehouse_name = form_data.get('warehouse_name', 'All Warehouses')
        report_mode = form_data.get('report_mode', 'consolidated')

        # Apply single warehouse filter if needed
        account_res = self._get_accounts(
            accounts, display_account, analytic_account_ids if report_mode == 'single' else None
        )

        # Get journal codes
        codes = []
        if form_data.get('journal_ids'):
            journals = self.env['account.journal'].browse(form_data['journal_ids'])
            codes = [j.code for j in journals if j.code]

        total_debit = sum(acc.get('debit') or 0.0 for acc in account_res)
        total_credit = sum(acc.get('credit') or 0.0 for acc in account_res)
        total_balance = sum(acc.get('balance') or 0.0 for acc in account_res)

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

# -*- coding: utf-8 -*-
from odoo import api, models


class ReportFinancialInherit(models.AbstractModel):
    _inherit = 'report.accounting_pdf_reports.report_financial'

    def _compute_account_balance(self, accounts):
        """Compute balance/debit/credit for provided accounts, filtered by analytic accounts if in context."""
        mapping = {
            'balance': "COALESCE(SUM(debit),0) - COALESCE(SUM(credit), 0) as balance",
            'debit': "COALESCE(SUM(debit), 0) as debit",
            'credit': "COALESCE(SUM(credit), 0) as credit",
        }

        res = {account.id: dict.fromkeys(mapping, 0.0) for account in accounts}
        if not accounts:
            return res

        tables, where_clause, where_params = self.env['account.move.line']._query_get()
        tables = tables.replace('"', '') if tables else 'account_move_line'

        wheres = []
        if where_clause.strip():
            wheres.append(where_clause.strip())
        filters = ' AND '.join(wheres) if wheres else '1=1'

        analytic_account_ids = self.env.context.get('analytic_account_ids')
        params = [tuple(accounts.ids)]

        # ✅ Simple direct filter (no need for subquery)
        analytic_filter = ''
        if analytic_account_ids:
            analytic_account_ids = tuple(analytic_account_ids)
            analytic_filter = ' AND account_move_line.analytic_account_id IN %s'
            params.append(analytic_account_ids)

        params += where_params

        query = f"""
            SELECT account_id as id, {', '.join(mapping.values())}
            FROM {tables}
            WHERE account_id IN %s AND {filters} {analytic_filter}
            GROUP BY account_id
        """

        self.env.cr.execute(query, tuple(params))
        for row in self.env.cr.dictfetchall():
            res[row['id']] = row

        return res

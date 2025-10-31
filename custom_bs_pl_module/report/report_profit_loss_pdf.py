# -*- coding: utf-8 -*-
from odoo import models, api
import json


class ReportProfitLossPDF(models.AbstractModel):
    _name = 'report.custom_bs_pl_module.report_profit_loss_pdf'
    _description = 'Custom Profit and Loss PDF Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Include warehouse analytic breakdown for Profit & Loss using analytic_distribution"""

        docs = self.env['account.balance.report'].browse(docids)
        data = data or {}

        all_warehouse_data = []
        combined_totals = {'debit': 0.0, 'credit': 0.0, 'balance': 0.0}

        for doc in docs:
            if hasattr(doc, 'warehouse_analytic_ids') and doc.warehouse_analytic_ids:
                # Loop through each selected warehouse analytic account
                for analytic in doc.warehouse_analytic_ids:
                    # ✅ Query using analytic_distribution (JSON field in Odoo 19)
                    query = """
                        SELECT
                            SUM(aml.debit) AS debit,
                            SUM(aml.credit) AS credit,
                            SUM(aml.debit - aml.credit) AS balance
                        FROM account_move_line aml
                        JOIN account_move am ON aml.move_id = am.id
                        JOIN account_account aa ON aml.account_id = aa.id
                        WHERE am.state = 'posted'
                          AND aml.company_id = %s
                          AND aml.analytic_distribution IS NOT NULL
                          AND aml.analytic_distribution::text LIKE %s
                    """

                    params = [doc.company_id.id, f'%"{analytic.id}"%']

                    # Add date filters
                    if doc.date_from:
                        query += " AND aml.date >= %s"
                        params.append(doc.date_from)

                    if doc.date_to:
                        query += " AND aml.date <= %s"
                        params.append(doc.date_to)

                    # Filter only P&L accounts
                    query += """
                        AND aa.account_type IN (
                            'income', 'income_other',
                            'expense', 'expense_depreciation', 'expense_direct_cost'
                        )
                    """

                    self.env.cr.execute(query, tuple(params))
                    row = self.env.cr.dictfetchone() or {}

                    warehouse_data = {
                        'warehouse_name': analytic.name,
                        'debit': row.get('debit', 0.0) or 0.0,
                        'credit': row.get('credit', 0.0) or 0.0,
                        'balance': row.get('balance', 0.0) or 0.0,
                    }
                    all_warehouse_data.append(warehouse_data)

                    combined_totals['debit'] += warehouse_data['debit']
                    combined_totals['credit'] += warehouse_data['credit']
                    combined_totals['balance'] += warehouse_data['balance']
            else:
                # No analytics selected → Show combined view
                query = """
                    SELECT
                        SUM(aml.debit) AS debit,
                        SUM(aml.credit) AS credit,
                        SUM(aml.debit - aml.credit) AS balance
                    FROM account_move_line aml
                    JOIN account_move am ON aml.move_id = am.id
                    JOIN account_account aa ON aml.account_id = aa.id
                    WHERE am.state = 'posted'
                      AND aml.company_id = %s
                """

                params = [doc.company_id.id]

                if doc.date_from:
                    query += " AND aml.date >= %s"
                    params.append(doc.date_from)

                if doc.date_to:
                    query += " AND aml.date <= %s"
                    params.append(doc.date_to)

                query += """
                    AND aa.account_type IN (
                        'income', 'income_other',
                        'expense', 'expense_depreciation', 'expense_direct_cost'
                    )
                """

                self.env.cr.execute(query, tuple(params))
                row = self.env.cr.dictfetchone() or {}

                all_warehouse_data.append({
                    'warehouse_name': 'All Warehouses',
                    'debit': row.get('debit', 0.0) or 0.0,
                    'credit': row.get('credit', 0.0) or 0.0,
                    'balance': row.get('balance', 0.0) or 0.0,
                })

                combined_totals['debit'] = row.get('debit', 0.0) or 0.0
                combined_totals['credit'] = row.get('credit', 0.0) or 0.0
                combined_totals['balance'] = row.get('balance', 0.0) or 0.0

        data.update({
            'all_warehouse_data': all_warehouse_data,
            'combined_totals': combined_totals,
        })

        return {
            'doc_ids': docids,
            'doc_model': 'account.balance.report',
            'docs': docs,
            'data': data,
        }
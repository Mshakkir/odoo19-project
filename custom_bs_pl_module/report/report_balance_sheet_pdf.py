# -*- coding: utf-8 -*-
from odoo import models, api


class ReportBalanceSheetPDF(models.AbstractModel):
    _name = 'report.custom_bs_pl_module.report_balance_sheet_pdf'
    _description = 'Custom Balance Sheet PDF Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Include warehouse analytic breakdown + combined totals in PDF"""
        docs = self.env['accounting.report'].browse(docids)
        data = data or {}

        all_warehouse_data = []
        combined_totals = {'debit': 0.0, 'credit': 0.0, 'balance': 0.0}

        for doc in docs:
            # Check if warehouse analytics are selected
            if hasattr(doc, 'warehouse_analytic_ids') and doc.warehouse_analytic_ids:
                for analytic in doc.warehouse_analytic_ids:
                    # Build SQL query properly with conditional date filters
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
                          AND aml.analytic_account_id = %s
                    """

                    params = [doc.company_id.id, analytic.id]

                    # Add date filters conditionally
                    if doc.date_from:
                        query += " AND aml.date >= %s"
                        params.append(doc.date_from)

                    if doc.date_to:
                        query += " AND aml.date <= %s"
                        params.append(doc.date_to)

                    # Filter only Balance Sheet accounts
                    query += """
                        AND aa.account_type IN (
                            'asset_receivable', 'asset_cash', 'asset_current', 
                            'asset_non_current', 'asset_prepayments', 'asset_fixed',
                            'liability_payable', 'liability_credit_card', 
                            'liability_current', 'liability_non_current',
                            'equity', 'equity_unaffected'
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

                    # Accumulate totals
                    combined_totals['debit'] += warehouse_data['debit']
                    combined_totals['credit'] += warehouse_data['credit']
                    combined_totals['balance'] += warehouse_data['balance']
            else:
                # No analytics selected → Show combined data for all warehouses
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
                        'asset_receivable', 'asset_cash', 'asset_current', 
                        'asset_non_current', 'asset_prepayments', 'asset_fixed',
                        'liability_payable', 'liability_credit_card', 
                        'liability_current', 'liability_non_current',
                        'equity', 'equity_unaffected'
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

        # Update data dictionary for template
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

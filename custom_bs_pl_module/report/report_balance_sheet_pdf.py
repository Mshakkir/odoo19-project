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
            if hasattr(doc, 'warehouse_analytic_ids') and doc.warehouse_analytic_ids:
                for analytic in doc.warehouse_analytic_ids:
                    # Re-run same SQL filter per warehouse analytic
                    self.env.cr.execute(f"""
                        SELECT
                            SUM(aml.debit) AS debit,
                            SUM(aml.credit) AS credit,
                            SUM(aml.debit - aml.credit) AS balance
                        FROM account_move_line aml
                        JOIN account_move am ON aml.move_id = am.id
                        WHERE am.state = 'posted'
                          AND aml.company_id = %s
                          AND aml.analytic_account_id = %s
                          { "AND aml.date >= %s" if doc.date_from else "" }
                          { "AND aml.date <= %s" if doc.date_to else "" }
                    """, tuple(
                        [doc.company_id.id, analytic.id]
                        + ([doc.date_from] if doc.date_from else [])
                        + ([doc.date_to] if doc.date_to else [])
                    ))
                    row = self.env.cr.dictfetchone() or {}
                    all_warehouse_data.append({
                        'warehouse_name': analytic.name,
                        'debit': row.get('debit', 0.0),
                        'credit': row.get('credit', 0.0),
                        'balance': row.get('balance', 0.0),
                    })
                    combined_totals['debit'] += row.get('debit', 0.0)
                    combined_totals['credit'] += row.get('credit', 0.0)
                    combined_totals['balance'] += row.get('balance', 0.0)
            else:
                # No analytics → Combined only
                all_warehouse_data.append({
                    'warehouse_name': 'All Warehouses',
                    'debit': 0.0,
                    'credit': 0.0,
                    'balance': 0.0,
                })

        data.update({
            'all_warehouse_data': all_warehouse_data,
            'combined_totals': combined_totals,
        })

        return {
            'doc_ids': docids,
            'doc_model': 'accounting.report',
            'docs': docs,
            'data': data,
        }

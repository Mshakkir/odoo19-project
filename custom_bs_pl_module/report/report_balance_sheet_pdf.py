# -*- coding: utf-8 -*-
from odoo import models, api


class ReportBalanceSheetPDF(models.AbstractModel):
    _name = 'report.custom_bs_pl_module.report_balance_sheet_pdf'
    _description = 'Custom Balance Sheet PDF Report (Warehouse-wise)'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Compute warehouse-wise Balance Sheet values using analytic_distribution JSON"""
        docs = self.env['account.balance.report'].browse(docids)
        data = data or {}

        all_warehouse_data = []
        combined_totals = {'debit': 0.0, 'credit': 0.0, 'balance': 0.0}

        for doc in docs:
            # Loop through selected analytic (warehouse) accounts
            if hasattr(doc, 'warehouse_analytic_ids') and doc.warehouse_analytic_ids:
                for analytic in doc.warehouse_analytic_ids:
                    params = [doc.company_id.id, str(analytic.id)]
                    date_clauses = ""
                    if getattr(doc, 'date_from', None):
                        date_clauses += " AND aml.date >= %s"
                        params.append(doc.date_from)
                    if getattr(doc, 'date_to', None):
                        date_clauses += " AND aml.date <= %s"
                        params.append(doc.date_to)

                    # ✅ Use JSON operator to match analytic ID key
                    sql = f"""
                        SELECT
                            COALESCE(SUM(aml.debit * ((aml.analytic_distribution ->> %s)::float / 100)),0) AS debit,
                            COALESCE(SUM(aml.credit * ((aml.analytic_distribution ->> %s)::float / 100)),0) AS credit,
                            COALESCE(SUM((aml.debit - aml.credit) * ((aml.analytic_distribution ->> %s)::float / 100)),0) AS balance
                        FROM account_move_line aml
                        JOIN account_move am ON aml.move_id = am.id
                        WHERE am.state = 'posted'
                          AND aml.company_id = %s
                          AND aml.analytic_distribution ? %s
                          {date_clauses}
                    """
                    params = [str(analytic.id), str(analytic.id), str(analytic.id), doc.company_id.id, str(analytic.id)] + params[2:]
                    self.env.cr.execute(sql, tuple(params))
                    row = self.env.cr.dictfetchone() or {}
                    debit = row.get('debit', 0.0)
                    credit = row.get('credit', 0.0)
                    balance = row.get('balance', 0.0)

                    all_warehouse_data.append({
                        'warehouse_name': analytic.name,
                        'debit': debit,
                        'credit': credit,
                        'balance': balance,
                    })
                    combined_totals['debit'] += debit
                    combined_totals['credit'] += credit
                    combined_totals['balance'] += balance
            else:
                # No analytics selected → show company-wide totals
                params = [doc.company_id.id]
                date_clauses = ""
                if getattr(doc, 'date_from', None):
                    date_clauses += " AND aml.date >= %s"
                    params.append(doc.date_from)
                if getattr(doc, 'date_to', None):
                    date_clauses += " AND aml.date <= %s"
                    params.append(doc.date_to)

                sql = f"""
                    SELECT
                        COALESCE(SUM(aml.debit),0) AS debit,
                        COALESCE(SUM(aml.credit),0) AS credit,
                        COALESCE(SUM(aml.debit - aml.credit),0) AS balance
                    FROM account_move_line aml
                    JOIN account_move am ON aml.move_id = am.id
                    WHERE am.state = 'posted'
                      AND aml.company_id = %s
                      {date_clauses}
                """
                self.env.cr.execute(sql, tuple(params))
                row = self.env.cr.dictfetchone() or {}
                debit = row.get('debit', 0.0)
                credit = row.get('credit', 0.0)
                balance = row.get('balance', 0.0)

                all_warehouse_data.append({
                    'warehouse_name': 'All Warehouses',
                    'debit': debit,
                    'credit': credit,
                    'balance': balance,
                })
                combined_totals['debit'] += debit
                combined_totals['credit'] += credit
                combined_totals['balance'] += balance

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

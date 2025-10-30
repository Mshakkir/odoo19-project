# -*- coding: utf-8 -*-
from odoo import models, api

class ReportProfitLossPDF(models.AbstractModel):
    _name = 'report.custom_bs_pl_module.report_profit_loss_pdf'
    _description = 'Custom Profit and Loss PDF Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['accounting.report'].browse(docids)
        data = data or {}

        all_warehouse_data = []
        for doc in docs:
            if hasattr(doc, 'warehouse_analytic_ids') and doc.warehouse_analytic_ids:
                for analytic in doc.warehouse_analytic_ids:
                    self.env.cr.execute("""
                        SELECT
                            SUM(aml.debit) AS debit,
                            SUM(aml.credit) AS credit,
                            SUM(aml.debit - aml.credit) AS balance
                        FROM account_move_line aml
                        JOIN account_move am ON aml.move_id = am.id
                        WHERE am.state = 'posted'
                          AND aml.company_id = %s
                          AND aml.analytic_account_id = %s
                    """, (doc.company_id.id, analytic.id))
                    row = self.env.cr.dictfetchone() or {}
                    all_warehouse_data.append({
                        'warehouse_name': analytic.name,
                        'debit': row.get('debit', 0.0),
                        'credit': row.get('credit', 0.0),
                        'balance': row.get('balance', 0.0),
                    })
        data.update({'all_warehouse_data': all_warehouse_data})
        return {
            'doc_ids': docids,
            'doc_model': 'accounting.report',
            'docs': docs,
            'data': data,
        }

# -*- coding: utf-8 -*-
from odoo import models, api

class ReportBalanceSheetPDF(models.AbstractModel):
    _name = 'report.custom_bs_pl_module.report_balance_sheet_pdf'
    _description = 'Custom Balance Sheet PDF Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Pass all accounting report data (including warehouse/analytic info) to QWeb PDF."""
        docs = self.env['accounting.report'].browse(docids)

        # ✅ Prepare warehouse analytic info (single or multiple)
        warehouse_label = ''
        for doc in docs:
            # If Many2many (multiple warehouses)
            if hasattr(doc, 'warehouse_analytic_ids') and doc.warehouse_analytic_ids:
                warehouse_label = ', '.join(doc.warehouse_analytic_ids.mapped('name'))

            # If single field
            elif hasattr(doc, 'warehouse_analytic_id') and doc.warehouse_analytic_id:
                warehouse_label = doc.warehouse_analytic_id.name

        # ✅ Inject the label into report data
        if data is None:
            data = {}

        data['warehouse_analytic_label'] = warehouse_label

        return {
            'doc_ids': docids,
            'doc_model': 'accounting.report',
            'docs': docs,
            'data': data,
        }

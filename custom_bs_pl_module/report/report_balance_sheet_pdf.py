# -*- coding: utf-8 -*-
from odoo import models, api

class ReportBalanceSheetPDF(models.AbstractModel):
    _name = 'report.custom_bs_pl_module.report_balance_sheet_pdf'
    _description = 'Custom Balance Sheet PDF Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Pass all accounting report data including warehouse/analytic info to QWeb PDF."""
        docs = self.env['accounting.report'].browse(docids)

        if data is None:
            data = {}

        # ✅ Build warehouse label from Many2many field
        warehouse_label = ''
        for doc in docs:
            if doc.warehouse_analytic_ids:
                warehouse_names = doc.warehouse_analytic_ids.mapped('name')
                warehouse_label = ', '.join(warehouse_names)
                break  # Only process first doc

        # ✅ Inject warehouse label into data
        data['warehouse_analytic_label'] = warehouse_label

        return {
            'doc_ids': docids,
            'doc_model': 'accounting.report',
            'docs': docs,
            'data': data,
        }
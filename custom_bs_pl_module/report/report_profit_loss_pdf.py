# -*- coding: utf-8 -*-
from odoo import models, api


class ReportProfitLossPDF(models.AbstractModel):
    _name = 'report.custom_bs_pl_module.report_profit_loss_pdf'
    _description = 'Custom Profit and Loss PDF Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Pass warehouse info to Profit & Loss PDF"""
        docs = self.env['accounting.report'].browse(docids)

        if data is None:
            data = {}

        # ✅ Build warehouse label
        warehouse_label = ''
        for doc in docs:
            if doc.warehouse_analytic_ids:
                warehouse_names = doc.warehouse_analytic_ids.mapped('name')
                warehouse_label = ', '.join(warehouse_names)
                break

        data['warehouse_analytic_label'] = warehouse_label

        return {
            'doc_ids': docids,
            'doc_model': 'accounting.report',
            'docs': docs,
            'data': data,
        }
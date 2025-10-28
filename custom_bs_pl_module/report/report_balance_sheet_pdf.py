# -*- coding: utf-8 -*-
from odoo import models, api

class ReportBalanceSheetPDF(models.AbstractModel):
    _name = 'report.custom_bs_pl_module.report_balance_sheet_pdf'
    _description = 'Custom Balance Sheet PDF Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['accounting.report'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'accounting.report',
            'docs': docs,
            'data': data,
        }

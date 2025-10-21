from odoo import api, models

class CustomBalanceSheetReport(models.AbstractModel):
    _name = 'report.custom_balance_sheet.report_custom_balance_sheet_pdf'
    _description = 'Custom Balance Sheet PDF Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['custom.balance.sheet.line'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'custom.balance.sheet.line',
            'docs': docs,
            'data': data or {},
            'res_company': self.env.company,
        }

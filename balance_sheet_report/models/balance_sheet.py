from odoo import models, api

class BalanceSheetReport(models.AbstractModel):
    _name = 'report.balance_sheet_report.template_balance_sheet'
    _description = 'Balance Sheet Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['account.move'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'account.move',
            'docs': docs,
        }

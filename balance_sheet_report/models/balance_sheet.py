from odoo import models, fields, api
from datetime import date

class AccountBalanceSheet(models.Model):
    _name = "account.balance.sheet"
    _description = "Balance Sheet"

    name = fields.Char(string="Name", default="Balance Sheet")
    date_from = fields.Date(string="From Date", required=True, default=date.today)
    date_to = fields.Date(string="To Date", required=True, default=date.today)

    def action_generate_report(self):
        return self.env.ref('balance_sheet_report.action_report_balance_sheet').report_action(self)


class BalanceSheetReport(models.AbstractModel):
    _name = 'report.balance_sheet_report.template_balance_sheet'
    _description = 'Balance Sheet Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['account.balance.sheet'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'account.balance.sheet',
            'docs': docs,
        }

from odoo import models, api, fields
from datetime import date

class AccountTaxReport(models.TransientModel):
    _name = 'account.tax.report.wizard'
    _inherit = "account.common.report"
    _description = 'Tax Report'

    date_from = fields.Date(
        string='Date From', required=True,
        default=lambda self: fields.Date.to_string(date.today().replace(day=1))
    )
    date_to = fields.Date(
        string='Date To', required=True,
        default=lambda self: fields.Date.to_string(date.today())
    )

    # NEW: option to choose Normal (summary) or Details
    report_option = fields.Selection([
        ('normal', 'Normal (Summary)'),
        ('details', 'Details (Full)')
    ], string='Report Type', required=True, default='normal')

    def _print_report(self, data):
        # Build the data dict that will be passed to the report
        data = {
            'form': {
                'date_from': self.date_from,
                'date_to': self.date_to,
                'target_move': self.target_move,
                'company_id': self.company_id.id if self.company_id else self.env.company.id,
                'report_option': self.report_option,
            }
        }
        # Call the same report action (the report will branch based on 'report_option')
        return self.env.ref('accounting_pdf_reports.action_report_account_tax').report_action(self, data=data)

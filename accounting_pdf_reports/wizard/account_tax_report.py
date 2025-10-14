# from odoo import models, api, fields
# from datetime import date
#
#
# class AccountTaxReport(models.TransientModel):
#     _name = 'account.tax.report.wizard'
#     _inherit = "account.common.report"
#     _description = 'Tax Report'
#
#     date_from = fields.Date(
#         string='Date From', required=True,
#         default=lambda self: fields.Date.to_string(date.today().replace(day=1))
#     )
#     date_to = fields.Date(
#         string='Date To', required=True,
#         default=lambda self: fields.Date.to_string(date.today())
#     )
#
#     def _print_report(self, data):
#         return self.env.ref('accounting_pdf_reports.action_report_account_tax').report_action(self, data=data)

from odoo import models, fields, api
from datetime import date

class AccountTaxReportWizard(models.TransientModel):
    _name = 'account.tax.report.wizard'
    _inherit = "account.common.report"
    _description = 'Tax Report Wizard'

    date_from = fields.Date(
        string='Date From', required=True,
        default=lambda self: fields.Date.to_string(date.today().replace(day=1))
    )
    date_to = fields.Date(
        string='Date To', required=True,
        default=lambda self: fields.Date.to_string(date.today())
    )
    target_move = fields.Selection(
        [('all', 'All Entries'), ('posted', 'Posted Entries')],
        string='Target Moves', default='posted'
    )
    detailed_summary = fields.Boolean(
        string='Detailed Summary',
        help='Enable to view summary report with clickable tax details'
    )

    def _print_report(self, data=None):
        """Print report respecting detailed_summary checkbox"""
        self.ensure_one()
        if not data:
            data = {'form': self.read()[0]}
        data['form']['detailed_summary'] = self.detailed_summary
        return self.env.ref('accounting_pdf_reports.action_report_account_tax').report_action(self, data=data)

    def action_summary(self):
        """Generate report in summary (normal) mode"""
        self.ensure_one()
        self.detailed_summary = False  # turn off detailed summary
        data = {'form': self.read()[0]}
        return self.env.ref('accounting_pdf_reports.action_report_account_tax').report_action(self, data=data)

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
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AccountTaxReportWizard(models.TransientModel):
    _name = 'account.tax.report.wizard'
    _inherit = 'account.common.report'
    _description = 'Tax Report Wizard'

    date_from = fields.Date(string='Start Date')
    date_to = fields.Date(string='End Date')
    target_move = fields.Selection([
        ('posted', 'All Posted Entries'),
        ('all', 'All Entries'),
    ], string='Target Moves', default='posted')

    # ✅ Warehouse filter via analytic accounts
    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        'account_tax_report_analytic_rel',
        string='Warehouse (Analytic Accounts)',
    )

    def _print_report(self, data):
        data = self.pre_print_report(data)
        data['form'].update({
            'analytic_account_ids': self.analytic_account_ids.ids,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'target_move': self.target_move,
        })
        return self.env.ref('accounting_pdf_reports.action_report_tax').report_action(self, data=data)

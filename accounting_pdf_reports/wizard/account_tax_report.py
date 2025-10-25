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


from odoo import models, fields
from datetime import date


class AccountTaxReport(models.TransientModel):
    _name = 'account.tax.report.wizard'
    _inherit = "account.common.report"
    _description = 'Tax Report'

    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        'account_tax_report_wizard_analytic_rel',
        'wizard_id',
        'analytic_id',
        string='Analytic Account (Warehouse)'
    )

    def _print_report(self, data):
        data = self.read(['date_from', 'date_to', 'target_move', 'analytic_account_ids'])[0]
        return self.env.ref('accounting_pdf_reports.action_report_account_tax').report_action(self, data={'form': data})
from odoo import models, api, fields
from datetime import date


class AccountTaxReport(models.TransientModel):
    _name = 'account.tax.report.wizard'
    _inherit = "account.common.report"
    _description = 'Tax Report'

    analytic_account_ids = fields.Many2many(
        comodel_name='account.analytic.account',
        relation='account_tax_report_wizard_analytic_rel',
        column1='wizard_id',
        column2='analytic_id',
        string='Analytic Accounts',
        help='Filter the tax report by analytic accounts (warehouses/branches).',
    )

    date_from = fields.Date(
        string='Date From', required=True,
        default=lambda self: fields.Date.to_string(date.today().replace(day=1))
    )
    date_to = fields.Date(
        string='Date To', required=True,
        default=lambda self: fields.Date.to_string(date.today())
    )

    def _print_report(self, data):
        return self.env.ref('accounting_pdf_reports.action_report_account_tax').report_action(self, data=data)

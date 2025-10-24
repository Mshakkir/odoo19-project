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
    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        'account_tax_report_analytic_rel',
        string='Warehouse (Analytic Accounts)'
    )

    def check_report(self):
        """Override to pass analytic account data"""
        self.ensure_one()
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read(['date_from', 'date_to', 'target_move', 'analytic_account_ids'])[0]

        # Build used_context
        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context, lang=self.env.context.get('lang') or 'en_US')

        return self._print_report(data)

    def _build_contexts(self, data):
        """Build context with analytic accounts"""
        result = {}
        result['date_from'] = data['form']['date_from'] or False
        result['date_to'] = data['form']['date_to'] or False
        result['state'] = data['form'].get('target_move', 'all')
        result['strict_range'] = True

        # Add analytic account context
        if data['form'].get('analytic_account_ids'):
            result['analytic_account_ids'] = self.env['account.analytic.account'].browse(
                data['form']['analytic_account_ids']
            )

        return result

    def _print_report(self, data):
        return self.env.ref('accounting_pdf_reports.action_report_account_tax').report_action(
            self, data=data
        )
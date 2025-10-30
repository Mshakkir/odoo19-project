from odoo import fields, models, api, _
from odoo.exceptions import UserError

class AccountReportGeneralLedgerAnalytic(models.TransientModel):
    _inherit = "account.report.general.ledger"

    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        string='Analytic Accounts',
        help='Filter General Ledger entries by analytic accounts.'
    )

    def _print_report(self, data):
        """Override to pass analytic account info to custom report"""
        records, data = self._get_report_data(data)
        analytic_ids = self.read(['analytic_account_ids'])[0].get('analytic_account_ids', [])
        data['form']['analytic_account_ids'] = analytic_ids
        return self.env.ref('analytic_general_ledger.action_report_general_ledger_analytic').with_context(landscape=True).report_action(records, data=data)

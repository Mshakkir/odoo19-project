from odoo import api, fields, models

class AccountCashbookAnalyticWizard(models.TransientModel):
    _inherit = 'account.daybook.report'  # reuse daybook wizard

    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        'rel_cashbook_analytic_account_rel',
        'wizard_id',
        'analytic_id',
        string='Analytic Accounts'
    )

    def _print_report(self, data):
        """Extend report filter"""
        data = super(AccountCashbookAnalyticWizard, self)._print_report(data)
        data['form']['analytic_account_ids'] = self.analytic_account_ids.ids or []
        return data

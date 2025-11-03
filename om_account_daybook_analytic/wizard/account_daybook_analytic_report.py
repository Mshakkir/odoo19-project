from odoo import api, fields, models

class AccountDaybookAnalyticWizard(models.TransientModel):
    _inherit = 'account.daybook.report'  # 👈 inherit from the existing daybook wizard

    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        'rel_daybook_analytic_account_rel',   # short name to avoid long table name
        'wizard_id',
        'analytic_id',
        string='Analytic Accounts'
    )

    def _print_report(self, data):
        """Extend original report filter to include analytic accounts"""
        data = super(AccountDaybookAnalyticWizard, self)._print_report(data)

        if self.analytic_account_ids:
            data['form']['analytic_account_ids'] = self.analytic_account_ids.ids
        else:
            data['form']['analytic_account_ids'] = []

        return data

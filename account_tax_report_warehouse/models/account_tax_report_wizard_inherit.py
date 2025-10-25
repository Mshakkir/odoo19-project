from odoo import api, fields, models

class AccountTaxReportWizard(models.TransientModel):
    _inherit = "account.tax.report.wizard"

    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        string="Analytic Accounts (Warehouses)",
        help="Filter Tax Report based on selected warehouse analytic accounts."
    )

    @api.model
    def _get_report_values(self, docids, data=None):
        """Inject analytic filter into report context."""
        res = super()._get_report_values(docids, data=data)
        if data and data.get('form') and data['form'].get('analytic_account_ids'):
            analytic_ids = data['form']['analytic_account_ids']
            res['data']['form']['analytic_account_ids'] = analytic_ids
        return res

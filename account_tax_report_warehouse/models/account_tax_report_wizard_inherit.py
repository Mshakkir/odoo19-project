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
def _print_report(self):
    form_data = self.read(['date_from', 'date_to', 'target_move', 'analytic_account_ids'])[0]

    # Normalize analytic_account_ids
    analytic_ids = form_data.get('analytic_account_ids', [])
    if analytic_ids and isinstance(analytic_ids[0], (tuple, list)):
        analytic_ids = analytic_ids[0][2]  # get IDs from [(6, 0, [ids])]
    form_data['analytic_account_ids'] = analytic_ids

    return self.env.ref('accounting_pdf_reports.action_report_account_tax').report_action(self, data={'form': form_data})


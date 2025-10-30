from odoo import api, fields, models, _

class AccountingReportAnalytic(models.TransientModel):
    _name = 'accounting.report.analytic'
    _inherit = 'accounting.report'
    _description = 'Accounting Report (with Analytic filter)'

    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        'accounting_report_analytic_rel',  # unique relation table name
        'report_id',                       # column for this model
        'analytic_id',                     # column for analytic account
        string='Analytic Accounts',
        help='Filter the report by these analytic accounts'
    )

    def _print_report(self, data):
        data['form'].update(self.read([
            'date_from_cmp', 'debit_credit', 'date_to_cmp',
            'filter_cmp', 'account_report_id', 'enable_filter',
            'label_filter', 'target_move'
        ])[0])

        used_context = data['form'].get('used_context', {}) or {}

        if self.analytic_account_ids:
            used_context = dict(used_context)
            used_context['analytic_account_ids'] = self.analytic_account_ids.ids

        data['form']['used_context'] = used_context

        return self.env.ref(
            'accounting_pdf_reports.action_report_financial'
        ).report_action(self, data=data, config=False)

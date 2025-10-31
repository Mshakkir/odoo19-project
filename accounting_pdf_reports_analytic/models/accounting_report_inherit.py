from odoo import api, fields, models, _


class AccountingReport(models.TransientModel):
    _inherit = 'accounting.report'

    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        'accounting_report_analytic_rel',
        'report_id',
        'analytic_id',
        string='Analytic Accounts',
        help='Filter the report by these analytic accounts'
    )

    analytic_filter_mode = fields.Selection([
        ('separate', 'Show Separate Reports'),
        ('combined', 'Show Combined Report'),
    ], string='Analytic Display Mode', default='combined',
        help='Separate: Generate one report per analytic account\n'
             'Combined: Combine all selected analytic accounts in one report')

    def _print_report(self, data):
        data['form'].update(self.read([
            'date_from_cmp', 'debit_credit', 'date_to_cmp',
            'filter_cmp', 'account_report_id', 'enable_filter',
            'label_filter', 'target_move', 'analytic_filter_mode'
        ])[0])

        # Pass analytic account IDs to the report
        if self.analytic_account_ids:
            data['form']['analytic_account_ids'] = self.analytic_account_ids.ids
            data['form']['analytic_filter_mode'] = self.analytic_filter_mode

            # Update used_context
            used_context = data['form'].get('used_context', {})
            if isinstance(used_context, str):
                used_context = eval(used_context)

            used_context['analytic_account_ids'] = self.analytic_account_ids.ids
            data['form']['used_context'] = used_context

        return self.env.ref(
            'accounting_pdf_reports.action_report_financial'
        ).report_action(self, data=data)
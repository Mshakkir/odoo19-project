from odoo import api, fields, models, _

class AccountingReportAnalytic(models.TransientModel):
    _name = 'accounting.report.analytic'
    _inherit = 'accounting.report'
    _description = 'Accounting Report (with Analytic filter)'

    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        string='Analytic Accounts',
        help='Filter the report by these analytic accounts'
    )

    # Override _print_report to include analytic_account_ids into the used_context that the report uses
    def _print_report(self, data):
        # Call parent to keep existing behavior and to update data['form'] with common fields
        data['form'].update(self.read(['date_from_cmp', 'debit_credit', 'date_to_cmp',
                                      'filter_cmp', 'account_report_id', 'enable_filter',
                                      'label_filter', 'target_move'])[0])

        # Build or extend used_context in the form so report_financial uses it.
        # `report_financial.get_account_lines` does: self.with_context(data.get('used_context'))
        used_context = data['form'].get('used_context', {}) or {}

        # Put analytic ids as a plain list (the account.move.line._query_get() expects analytic_account_ids in context)
        if self.analytic_account_ids:
            used_context = dict(used_context)  # copy to avoid modifying other references
            used_context['analytic_account_ids'] = self.analytic_account_ids.ids

        data['form']['used_context'] = used_context

        # Now call the original report action using the same report action
        return self.env.ref('accounting_pdf_reports.action_report_financial').report_action(self, data=data, config=False)

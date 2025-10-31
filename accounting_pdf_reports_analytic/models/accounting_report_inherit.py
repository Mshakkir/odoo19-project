from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)


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
    _logger.info("=" * 80)
    _logger.info("PRINT REPORT CALLED")
    _logger.info(f"Analytic Account IDs selected: {self.analytic_account_ids.ids}")
    _logger.info(f"Analytic names: {self.analytic_account_ids.mapped('name')}")
    _logger.info(f"Filter mode: {self.analytic_filter_mode}")

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
            import ast
            try:
                used_context = ast.literal_eval(used_context)
            except:
                used_context = {}

        used_context['analytic_account_ids'] = self.analytic_account_ids.ids
        data['form']['used_context'] = used_context

    # Use different template based on mode
    if self.analytic_account_ids and self.analytic_filter_mode == 'separate':
        _logger.info("Using SEPARATE template")
        report = self.env.ref('accounting_pdf_reports_analytic.action_report_financial_separate_analytic')
    elif self.analytic_account_ids and self.analytic_filter_mode == 'combined':
        _logger.info("Using COMBINED ANALYTIC template")
        report = self.env.ref('accounting_pdf_reports_analytic.action_report_financial_combined_analytic')
    else:
        _logger.info("Using ORIGINAL template (no analytic)")
        report = self.env.ref('accounting_pdf_reports.action_report_financial')

    return report.report_action(self, data=data)
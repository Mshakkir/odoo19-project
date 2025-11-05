from odoo import fields, models, api, _


class AccountCashBookReport(models.TransientModel):
    _inherit = "account.cashbook.report"

    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        'cashbook_analytic_account_rel',
        'report_id',
        'analytic_account_id',
        string='Analytic Accounts',
        help='Filter by specific analytic accounts. Leave empty for all.'
    )

    report_type = fields.Selection([
        ('combined', 'Combined Report'),
        ('separate', 'Separate by Analytic Account'),
    ], string='Report Type', default='combined', required=True,
        help='Combined: Show all transactions grouped by analytic account\n'
             'Separate: Generate individual reports for each analytic account')

    group_by_analytic = fields.Boolean(
        string='Group by Analytic Account',
        default=True,
        help='When enabled, transactions will be grouped by analytic account'
    )

    def _build_comparison_context(self, data):
        """Override to add analytic account context"""
        result = super()._build_comparison_context(data)
        result['analytic_account_ids'] = data['form'].get('analytic_account_ids', [])
        result['report_type'] = data['form'].get('report_type', 'combined')
        result['group_by_analytic'] = data['form'].get('group_by_analytic', True)
        return result

    def check_report(self):
        """Override to use the new report with analytic accounts"""
        import logging
        _logger = logging.getLogger(__name__)

        data = {}
        data['form'] = self.read([
            'target_move', 'date_from', 'date_to', 'journal_ids',
            'account_ids', 'sortby', 'initial_balance', 'display_account',
            'analytic_account_ids', 'report_type', 'group_by_analytic'
        ])[0]

        # ✅ Convert Many2many fields to list of IDs (they come as list of tuples from read())
        if data['form'].get('journal_ids'):
            data['form']['journal_ids'] = data['form']['journal_ids']

        if data['form'].get('account_ids'):
            data['form']['account_ids'] = data['form']['account_ids']

        if data['form'].get('analytic_account_ids'):
            data['form']['analytic_account_ids'] = data['form']['analytic_account_ids']

        # Debug logging
        _logger.warning("=" * 80)
        _logger.warning("WIZARD DATA BEING PASSED TO REPORT:")
        _logger.warning("Date From: %s", data['form'].get('date_from'))
        _logger.warning("Date To: %s", data['form'].get('date_to'))
        _logger.warning("Report Type: %s", data['form'].get('report_type'))
        _logger.warning("Analytic Account IDs: %s", data['form'].get('analytic_account_ids'))
        _logger.warning("Journal IDs: %s", data['form'].get('journal_ids'))
        _logger.warning("Account IDs: %s", data['form'].get('account_ids'))
        _logger.warning("Target Move: %s", data['form'].get('target_move'))
        _logger.warning("=" * 80)

        comparison_context = self._build_comparison_context(data)
        data['form']['comparison_context'] = comparison_context

        # ✅ Pass the data to the report
        return self.env.ref('om_cashbook_analytic.action_report_cash_book_analytic').report_action(self, data=data)
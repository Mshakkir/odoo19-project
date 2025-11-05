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

        # First, let's test if we can query data directly
        _logger.warning("=" * 80)
        _logger.warning("TESTING DATABASE QUERY FROM WIZARD")

        # Test query to see if we have any matching records
        test_query = """
            SELECT COUNT(*) as count
            FROM account_move_line l
            JOIN account_journal j ON (l.journal_id = j.id)
            WHERE j.type IN ('cash', 'bank')
              AND l.date BETWEEN %s AND %s
              AND l.analytic_distribution IS NOT NULL
        """
        self.env.cr.execute(test_query, (self.date_from, self.date_to))
        test_result = self.env.cr.fetchone()
        _logger.warning("Found %s move lines with analytic distribution in date range",
                        test_result[0] if test_result else 0)

        # Check if analytic account exists and has data
        if self.analytic_account_ids:
            for analytic in self.analytic_account_ids:
                _logger.warning("Analytic Account: ID=%s, Name=%s", analytic.id, analytic.name)

                # Check if this analytic account is used in any transactions
                check_query = """
                    SELECT COUNT(*) as count
                    FROM account_move_line l
                    WHERE l.analytic_distribution ? %s
                      AND l.date BETWEEN %s AND %s
                """
                self.env.cr.execute(check_query, (str(analytic.id), self.date_from, self.date_to))
                analytic_result = self.env.cr.fetchone()
                _logger.warning("  -> Found %s move lines for this analytic account",
                                analytic_result[0] if analytic_result else 0)

        _logger.warning("=" * 80)

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

        # Try to find and verify the report exists
        try:
            report = self.env.ref('om_cashbook_analytic.action_report_cash_book_analytic')
            _logger.warning("Found report: %s (ID: %s)", report.name, report.id)
            _logger.warning("Report model: %s", report.model)
            _logger.warning("Report name: %s", report.report_name)

            # ✅ Pass the data to the report
            result = report.report_action(self, data=data)
            _logger.warning("Report action result: %s", result)
            return result
        except Exception as e:
            _logger.error("Error calling report: %s", str(e), exc_info=True)
            raise
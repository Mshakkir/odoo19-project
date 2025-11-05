from odoo import fields, models, api


class AccountCashBookReportAnalytic(models.TransientModel):
    _inherit = "account.cashbook.report"

    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        'cashbook_analytic_account_rel',
        'cashbook_id',
        'analytic_account_id',
        string='Analytic Accounts',
        help='Filter entries by analytic accounts. Leave empty to show all entries.'
    )

    def _build_comparison_context(self, data):
        """Override to add analytic account filter to context"""
        result = super(AccountCashBookReportAnalytic, self)._build_comparison_context(data)
        result['analytic_account_ids'] = data['form'].get('analytic_account_ids', False)
        return result

    def check_report(self):
        """Override to include analytic account data"""
        data = {}
        data['form'] = self.read([
            'target_move', 'date_from', 'date_to', 'journal_ids',
            'account_ids', 'sortby', 'initial_balance',
            'display_account', 'analytic_account_ids'
        ])[0]
        comparison_context = self._build_comparison_context(data)
        data['form']['comparison_context'] = comparison_context
        return self.env.ref(
            'om_account_daily_reports.action_report_cash_book'
        ).report_action(self, data=data)
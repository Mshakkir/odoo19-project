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


def action_show_details(self):
    """Show detailed move lines with proper analytic account filtering"""
    domain = []

    # Filter by journals - get cash journal accounts
    if self.journal_ids:
        # Get cash accounts from selected journals
        cash_accounts = self.env['account.account']
        for journal in self.journal_ids:
            for acc_out in journal.outbound_payment_method_line_ids:
                if acc_out.payment_account_id:
                    cash_accounts += acc_out.payment_account_id
            for acc_in in journal.inbound_payment_method_line_ids:
                if acc_in.payment_account_id:
                    cash_accounts += acc_in.payment_account_id

        if cash_accounts:
            domain.append(('account_id', 'in', cash_accounts.ids))

    # Filter by date range
    if self.date_from:
        domain.append(('date', '>=', self.date_from))
    if self.date_to:
        domain.append(('date', '<=', self.date_to))

    # Filter by specific accounts if selected
    if self.account_ids:
        domain.append(('account_id', 'in', self.account_ids.ids))

    # Filter by analytic accounts using proper JSONB query
    if self.analytic_account_ids:
        # Build OR condition for multiple analytic accounts
        analytic_domain = []
        for analytic in self.analytic_account_ids:
            analytic_domain.append(('analytic_distribution', '?', str(analytic.id)))

        if len(analytic_domain) == 1:
            domain.extend(analytic_domain)
        else:
            domain.append('|' * (len(analytic_domain) - 1))
            domain.extend(analytic_domain)

    # Filter only posted moves if target_move is 'posted'
    if self.target_move == 'posted':
        domain.append(('move_id.state', '=', 'posted'))

    return {
        'type': 'ir.actions.act_window',
        'name': 'Cashbook Analytic Details',
        'res_model': 'account.move.line',
        'view_mode': 'list',  # ✅ Only one view mode when view_id is specified
        'domain': domain,
        'context': {
            'search_default_group_by_move_id': 1,
        },
        'target': 'current',
        'view_id': self.env.ref('cashbook_analytic_account.view_account_move_line_cashbook_analytic_tree').id,
    }
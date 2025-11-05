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
        """Open detailed account move lines filtered by analytic account and other fields"""
        domain = [('journal_id', 'in', self.journal_ids.ids)]

        # Add date range
        if self.date_from:
            domain.append(('date', '>=', self.date_from))
        if self.date_to:
            domain.append(('date', '<=', self.date_to))

        # Add analytic filter
        if self.analytic_account_ids:
            domain.append(('analytic_distribution', '!=', False))
            # Add JSON-based analytic filter (Odoo 17/18/19 stores analytic distribution in JSON)
            analytic_ids = [str(aid.id) for aid in self.analytic_account_ids]
            domain.append(('analytic_distribution', 'ilike', analytic_ids[0]))  # Simple contains filter

        # Add accounts filter
        if self.account_ids:
            domain.append(('account_id', 'in', self.account_ids.ids))

        # Action to open tree view
        return {
            'type': 'ir.actions.act_window',
            'name': 'Cashbook Analytic Details',
            'res_model': 'account.move.line',
            'view_mode': 'list',
            'domain': domain,
            'context': {'search_default_group_by_move_id': 1},
            'target': 'current',
        }

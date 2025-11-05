from odoo import fields, models, api

import logging

_logger = logging.getLogger(__name__)

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

    import logging
    _logger = logging.getLogger(__name__)


def action_show_details(self):
    domain = [('journal_id', 'in', self.journal_ids.ids)]

    if self.date_from:
        domain.append(('date', '>=', self.date_from))
    if self.date_to:
        domain.append(('date', '<=', self.date_to))

    # Analytic filter
    if self.analytic_account_ids:
        domain.append(('analytic_distribution', '!=', False))
        for analytic in self.analytic_account_ids:
            domain.append(('analytic_distribution', 'ilike', f'"{analytic.id}"'))

    if self.account_ids:
        domain.append(('account_id', 'in', self.account_ids.ids))

    _logger.info("🔍 Domain Used for Cashbook Analytic: %s", domain)

    return {
        'type': 'ir.actions.act_window',
        'name': 'Cashbook Analytic Details',
        'res_model': 'account.move.line',
        'view_mode': 'list',
        'domain': domain,
        'context': {'search_default_group_by_move_id': 1},
        'target': 'current',
        'view_id': self.env.ref('cashbook_analytic_account.view_account_move_line_cashbook_analytic_tree').id,
    }


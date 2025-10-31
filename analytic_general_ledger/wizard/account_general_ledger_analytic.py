from odoo import fields, models, api, _
from odoo.exceptions import UserError

class AccountReportGeneralLedgerAnalytic(models.TransientModel):
    _inherit = "account.report.general.ledger"

    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        string='Analytic Accounts',
        help='Filter General Ledger entries by analytic accounts.'
    )

    def _print_report(self, data):
        """Override to pass analytic account info to custom report"""
        records, data = self._get_report_data(data)
        analytic_ids = self.read(['analytic_account_ids'])[0].get('analytic_account_ids', [])
        data['form']['analytic_account_ids'] = analytic_ids
        return self.env.ref('accounting_pdf_reports.action_report_general_ledger').with_context(
            landscape=True).report_action(records, data=data)

def action_show_details(self):
    """Open general ledger move lines filtered by analytic accounts and dates."""
    self.ensure_one()

    # Collect filter criteria
    analytic_ids = self.analytic_account_ids.ids
    date_from = self.date_from
    date_to = self.date_to

    domain = []
    if analytic_ids:
        domain.append(('analytic_account_id', 'in', analytic_ids))
    if date_from:
        domain.append(('date', '>=', date_from))
    if date_to:
        domain.append(('date', '<=', date_to))

    # Optional: Filter only posted moves
    domain.append(('move_id.state', '=', 'posted'))

    return {
        'type': 'ir.actions.act_window',
        'name': _('General Ledger Details'),
        'res_model': 'account.move.line',
        'view_mode': 'tree,form',
        'domain': domain,
        'context': {
            'search_default_group_by_account_id': 1,  # Group by account in list view
        },
        'target': 'current',
    }

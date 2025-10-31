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

    # ------------------------------------------------------------
    # 👇 This part enables your "Show Details" button in the XML
    # ------------------------------------------------------------
def open_general_ledger_details(self):
    """
    Called when the 'Show Details' button is clicked.
    Opens account move lines filtered by analytic accounts,
    journals, and date range.
    """
    self.ensure_one()

    domain = []

    if self.analytic_account_ids:
        domain.append(('analytic_account_id', 'in', self.analytic_account_ids.ids))
    if self.journal_ids:
        domain.append(('journal_id', 'in', self.journal_ids.ids))
    if self.date_from:
        domain.append(('date', '>=', self.date_from))
    if self.date_to:
        domain.append(('date', '<=', self.date_to))

    return {
        'type': 'ir.actions.act_window',
        'name': _('Analytic Ledger Details'),
        'res_model': 'account.move.line',
        'views': [(False, 'tree'), (False, 'form')],   # ✅ Add this line
        'view_mode': 'tree,form',                      # ✅ Add this line too
        'domain': domain,
        'target': 'current',
    }


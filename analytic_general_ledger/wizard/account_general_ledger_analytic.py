# from odoo import fields, models, api, _
# from odoo.exceptions import UserError
#
# class AccountReportGeneralLedgerAnalytic(models.TransientModel):
#     _inherit = "account.report.general.ledger"
#
#     analytic_account_ids = fields.Many2many(
#         'account.analytic.account',
#         string='Analytic Accounts',
#         help='Filter General Ledger entries by analytic accounts.'
#     )
#
#     def _print_report(self, data):
#         """Override to pass analytic account info to custom report"""
#         records, data = self._get_report_data(data)
#         analytic_ids = self.read(['analytic_account_ids'])[0].get('analytic_account_ids', [])
#         data['form']['analytic_account_ids'] = analytic_ids
#         return self.env.ref('accounting_pdf_reports.action_report_general_ledger').with_context(
#             landscape=True).report_action(records, data=data)
#

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

    def check_report_analytic(self):
        """Open detailed view of general ledger with analytic accounts"""
        self.ensure_one()

        # Build domain for filtering
        domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ]

        # Add journal filter
        if self.journal_ids:
            domain.append(('journal_id', 'in', self.journal_ids.ids))

        # Add analytic account filter
        if self.analytic_account_ids:
            domain.append(('analytic_account_id', 'in', self.analytic_account_ids.ids))

        # Add target move filter
        if self.target_move == 'posted':
            domain.append(('move_id.state', '=', 'posted'))

        # Add display account filter
        if self.display_account == 'not_zero':
            # This will be handled in the view
            pass
        elif self.display_account == 'movement':
            domain.append('|')
            domain.append(('debit', '!=', 0))
            domain.append(('credit', '!=', 0))

        return {
            'name': _('General Ledger Details (Analytic)'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'tree',
            'view_id': self.env.ref('analytic_general_ledger.view_general_ledger_analytic_line_tree').id,
            'domain': domain,
            'context': {
                'search_default_group_by_account': 1,
            },
            'target': 'current',
        }
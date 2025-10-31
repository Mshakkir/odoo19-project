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

        # Build base domain
        domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ]

        # Add journal filter
        if self.journal_ids:
            domain.append(('journal_id', 'in', self.journal_ids.ids))

        # Add target move filter
        if self.target_move == 'posted':
            domain.append(('parent_state', '=', 'posted'))

        # Get move lines
        if self.analytic_account_ids:
            # Need to filter by analytic distribution
            # First get all lines matching other criteria
            all_lines = self.env['account.move.line'].search(domain)

            # Filter by analytic accounts
            filtered_line_ids = []
            for line in all_lines:
                if line.analytic_distribution:
                    # Check if any selected analytic account is in the distribution
                    for analytic_id in self.analytic_account_ids.ids:
                        if str(analytic_id) in str(line.analytic_distribution):
                            filtered_line_ids.append(line.id)
                            break

            line_ids = filtered_line_ids
        else:
            # Just get all lines matching domain
            line_ids = self.env['account.move.line'].search(domain).ids

        # Apply display account filter
        if self.display_account == 'movement' and line_ids:
            lines = self.env['account.move.line'].browse(line_ids)
            line_ids = [l.id for l in lines if l.debit != 0 or l.credit != 0]

        if not line_ids:
            raise UserError(_('No journal entries found for the selected criteria.\n\n'
                              'Please check:\n'
                              '- Date range has transactions\n'
                              '- Selected journals have entries\n'
                              '- Analytic accounts are assigned to journal entries'))

        return {
            'name': _('General Ledger Details (Analytic)'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'list',
            'view_id': self.env.ref('analytic_general_ledger.view_general_ledger_analytic_line_tree').id,
            'domain': [('id', 'in', line_ids)],
            'context': {
                'search_default_group_by_account': 1,
            },
            'target': 'current',
        }
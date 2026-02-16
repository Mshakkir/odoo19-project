from odoo import fields, models, api, _
from odoo.exceptions import UserError
import json


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

        # Add account filter - THIS IS THE KEY FIX
        if self.account_ids:
            domain.append(('account_id', 'in', self.account_ids.ids))

        # Add journal filter
        if self.journal_ids:
            domain.append(('journal_id', 'in', self.journal_ids.ids))

        # Add target move filter
        if self.target_move == 'posted':
            domain.append(('parent_state', '=', 'posted'))

        # Get move lines
        all_lines = self.env['account.move.line'].search(domain)

        # Filter by analytic accounts if specified
        if self.analytic_account_ids:
            filtered_line_ids = []
            selected_analytic_ids = set(self.analytic_account_ids.ids)

            for line in all_lines:
                if line.analytic_distribution:
                    try:
                        # Parse the JSON analytic_distribution
                        if isinstance(line.analytic_distribution, str):
                            distribution = json.loads(line.analytic_distribution)
                        else:
                            distribution = line.analytic_distribution

                        # Get analytic account IDs from the distribution
                        line_analytic_ids = set(int(k) for k in distribution.keys())

                        # Check if any of the selected analytic accounts are in this line
                        if selected_analytic_ids & line_analytic_ids:  # Intersection
                            filtered_line_ids.append(line.id)
                    except (json.JSONDecodeError, ValueError, AttributeError):
                        # Skip lines with invalid analytic_distribution
                        continue

            line_ids = filtered_line_ids
        else:
            # If no analytic filter, show all lines
            line_ids = all_lines.ids

        # Apply display account filter
        if self.display_account == 'movement' and line_ids:
            lines = self.env['account.move.line'].browse(line_ids)
            line_ids = [l.id for l in lines if l.debit != 0 or l.credit != 0]

        if not line_ids:
            # Build helpful error message
            error_msg = _('No journal entries found for the selected criteria.\n\nPlease check:')
            error_details = []
            error_details.append(f'- Date range: {self.date_from} to {self.date_to}')
            if self.account_ids:
                error_details.append(f'- Accounts: {", ".join(self.account_ids.mapped("code"))}')
            if self.journal_ids:
                error_details.append(f'- Journals: {", ".join(self.journal_ids.mapped("name"))}')
            if self.analytic_account_ids:
                error_details.append(f'- Analytic Accounts: {", ".join(self.analytic_account_ids.mapped("name"))}')
            error_details.append('- Make sure journal entries have analytic distribution assigned')

            raise UserError(error_msg + '\n' + '\n'.join(error_details))

        # Build context with analytic account names for display
        context = {
            'search_default_group_by_account': 1,
        }

        # Build a descriptive name
        title = _('General Ledger Details')
        title_parts = []

        if self.account_ids:
            account_names = ', '.join(self.account_ids.mapped('code'))
            title_parts.append(account_names)

        if self.analytic_account_ids:
            analytic_names = ', '.join(self.analytic_account_ids.mapped('name'))
            title_parts.append(f'Analytic: {analytic_names}')

        if title_parts:
            title += ' - ' + ' | '.join(title_parts)

        return {
            'name': title,
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'list',
            'view_id': self.env.ref('analytic_general_ledger.view_general_ledger_analytic_line_tree').id,
            'domain': [('id', 'in', line_ids)],
            'context': context,
            'target': 'current',
        }
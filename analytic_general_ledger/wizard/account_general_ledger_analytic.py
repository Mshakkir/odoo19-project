from odoo import fields, models, api, _
from odoo.exceptions import UserError
import json


class AccountGeneralLedgerLine(models.TransientModel):
    """Transient model to display rate-converted GL lines in the detail view"""
    _name = 'account.general.ledger.line'
    _description = 'General Ledger Detail Line (Converted)'
    _order = 'account_code, date, id'

    wizard_id = fields.Many2one('account.report.general.ledger', ondelete='cascade')
    date = fields.Date(string='Date', readonly=True)
    move_name = fields.Char(string='Journal Entry', readonly=True)
    journal_code = fields.Char(string='Journal', readonly=True)
    account_code = fields.Char(string='Account', readonly=True)
    account_name = fields.Char(string='Account Name', readonly=True)
    analytic_distribution = fields.Char(string='Analytic Distribution', readonly=True)
    partner_name = fields.Char(string='Partner', readonly=True)
    label = fields.Char(string='Label', readonly=True)
    debit = fields.Float(string='Debit', readonly=True)
    credit = fields.Float(string='Credit', readonly=True)
    balance = fields.Float(string='Balance', readonly=True)
    move_id = fields.Integer(string='Move ID', readonly=True)

    def action_open_move(self):
        self.ensure_one()
        if not self.move_id:
            return {}
        return {
            'name': _('Journal Entry'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.move_id,
            'view_mode': 'form',
            'target': 'current',
        }


class AccountReportGeneralLedgerAnalytic(models.TransientModel):
    _inherit = "account.report.general.ledger"

    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        string='Analytic Accounts',
        help='Filter General Ledger entries by analytic accounts.'
    )

    def _print_report(self, data):
        """Override to use our custom report that applies manual exchange rate"""
        records, data = self._get_report_data(data)
        analytic_ids = self.read(['analytic_account_ids'])[0].get('analytic_account_ids', [])
        data['form']['analytic_account_ids'] = analytic_ids
        return self.env.ref(
            'analytic_general_ledger.action_report_general_ledger_analytic'
        ).with_context(landscape=True).report_action(records, data=data)

    def _get_converted_lines(self):
        """
        Use ORM to fetch account.move.line records, then raw SQL only for
        payment rate — avoids any dependency on DB column names of account_account.
        """
        domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('parent_state', '=', 'posted'),
        ]
        if self.account_ids:
            domain.append(('account_id', 'in', self.account_ids.ids))
        if self.journal_ids:
            domain.append(('journal_id', 'in', self.journal_ids.ids))

        all_lines = self.env['account.move.line'].search(domain, order='account_id, date, id')

        # Analytic filter (Python-side, safe)
        if self.analytic_account_ids:
            selected_ids = set(self.analytic_account_ids.ids)
            filtered = []
            for line in all_lines:
                if line.analytic_distribution:
                    try:
                        dist = line.analytic_distribution if isinstance(line.analytic_distribution, dict) \
                            else json.loads(line.analytic_distribution)
                        if selected_ids & set(int(k) for k in dist.keys()):
                            filtered.append(line)
                    except Exception:
                        pass
            all_lines = self.env['account.move.line'].browse([l.id for l in filtered])

        if not all_lines:
            return []

        # Fetch manual exchange rates for all involved moves in one SQL query
        # Only need move_id -> (rate, payment_currency_id, company_currency_id)
        move_ids = list(set(all_lines.mapped('move_id').ids))
        rate_map = {}  # move_id -> rate multiplier (1.0 if no conversion needed)

        if move_ids:
            cr = self.env.cr
            cr.execute("""
                SELECT
                    pay.move_id,
                    COALESCE(pay.manual_currency_exchange_rate, 0.0) AS rate,
                    pay.currency_id AS pay_cur,
                    comp.currency_id AS comp_cur
                FROM account_payment pay
                JOIN account_move m ON m.id = pay.move_id
                JOIN res_company comp ON comp.id = m.company_id
                WHERE pay.move_id IN %s
            """, (tuple(move_ids),))
            for row in cr.dictfetchall():
                rate = row['rate']
                if rate and rate > 0.0 and row['pay_cur'] and row['comp_cur'] \
                        and row['pay_cur'] != row['comp_cur']:
                    rate_map[row['move_id']] = rate
                else:
                    rate_map[row['move_id']] = 1.0

        # Build result rows using ORM field access (no raw column name issues)
        rows = []
        for line in all_lines:
            rate = rate_map.get(line.move_id.id, 1.0)
            debit = line.debit * rate
            credit = line.credit * rate
            balance = debit - credit

            # Analytic distribution as string for display
            analytic_str = ''
            if line.analytic_distribution:
                try:
                    dist = line.analytic_distribution if isinstance(line.analytic_distribution, dict) \
                        else json.loads(line.analytic_distribution)
                    analytic_ids = [int(k) for k in dist.keys()]
                    analytic_str = ', '.join(
                        self.env['account.analytic.account'].browse(analytic_ids).mapped('name')
                    )
                except Exception:
                    pass

            rows.append({
                'ldate': line.date,
                'move_name': line.move_id.name or '',
                'move_id': line.move_id.id,
                'journal_code': line.journal_id.code or '',
                'account_code': line.account_id.code or '',
                'account_name': line.account_id.name or '',
                'analytic_distribution': analytic_str,
                'partner_name': line.partner_id.name or '',
                'label': line.name or '',
                'debit': debit,
                'credit': credit,
                'balance': balance,
            })

        return rows

    def check_report_analytic(self):
        """Open detailed view with rate-converted amounts"""
        self.ensure_one()

        rows = self._get_converted_lines()

        if not rows:
            error_msg = _('No journal entries found for the selected criteria.\n\nPlease check:')
            details = [f'- Date range: {self.date_from} to {self.date_to}']
            if self.account_ids:
                details.append(f'- Accounts: {", ".join(self.account_ids.mapped("code"))}')
            if self.journal_ids:
                details.append(f'- Journals: {", ".join(self.journal_ids.mapped("name"))}')
            if self.analytic_account_ids:
                details.append(f'- Analytic Accounts: {", ".join(self.analytic_account_ids.mapped("name"))}')
            raise UserError(error_msg + '\n' + '\n'.join(details))

        # Build running balance per account
        balance_tracker = {}
        line_vals = []
        for row in rows:
            acc = row['account_code']
            balance_tracker.setdefault(acc, 0.0)
            balance_tracker[acc] += row['balance']

            line_vals.append({
                'wizard_id': self.id,
                'date': row['ldate'],
                'move_name': row['move_name'],
                'journal_code': row['journal_code'],
                'account_code': row['account_code'],
                'account_name': row['account_name'],
                'analytic_distribution': row['analytic_distribution'],
                'partner_name': row['partner_name'],
                'label': row['label'],
                'debit': row['debit'],
                'credit': row['credit'],
                'balance': balance_tracker[acc],
                'move_id': row['move_id'],
            })

        lines = self.env['account.general.ledger.line'].create(line_vals)

        # Title
        title = _('General Ledger Details')
        parts = []
        if self.account_ids:
            parts.append(', '.join(self.account_ids.mapped('code')))
        if self.analytic_account_ids:
            parts.append('Analytic: ' + ', '.join(self.analytic_account_ids.mapped('name')))
        if parts:
            title += ' - ' + ' | '.join(parts)

        return {
            'name': title,
            'type': 'ir.actions.act_window',
            'res_model': 'account.general.ledger.line',
            'view_mode': 'list',
            'view_id': self.env.ref('analytic_general_ledger.view_general_ledger_converted_line_tree').id,
            'domain': [('id', 'in', lines.ids)],
            'context': {'search_default_group_by_account': 1},
            'target': 'current',
        }















# from odoo import fields, models, api, _
# from odoo.exceptions import UserError
# import json
#
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
#     def check_report_analytic(self):
#         """Open detailed view of general ledger with analytic accounts"""
#         self.ensure_one()
#
#         # Build base domain
#         domain = [
#             ('date', '>=', self.date_from),
#             ('date', '<=', self.date_to),
#         ]
#
#         # Add account filter - THIS IS THE KEY FIX
#         if self.account_ids:
#             domain.append(('account_id', 'in', self.account_ids.ids))
#
#         # Add journal filter
#         if self.journal_ids:
#             domain.append(('journal_id', 'in', self.journal_ids.ids))
#
#         # Add target move filter
#         if self.target_move == 'posted':
#             domain.append(('parent_state', '=', 'posted'))
#
#         # Get move lines
#         all_lines = self.env['account.move.line'].search(domain)
#
#         # Filter by analytic accounts if specified
#         if self.analytic_account_ids:
#             filtered_line_ids = []
#             selected_analytic_ids = set(self.analytic_account_ids.ids)
#
#             for line in all_lines:
#                 if line.analytic_distribution:
#                     try:
#                         # Parse the JSON analytic_distribution
#                         if isinstance(line.analytic_distribution, str):
#                             distribution = json.loads(line.analytic_distribution)
#                         else:
#                             distribution = line.analytic_distribution
#
#                         # Get analytic account IDs from the distribution
#                         line_analytic_ids = set(int(k) for k in distribution.keys())
#
#                         # Check if any of the selected analytic accounts are in this line
#                         if selected_analytic_ids & line_analytic_ids:  # Intersection
#                             filtered_line_ids.append(line.id)
#                     except (json.JSONDecodeError, ValueError, AttributeError):
#                         # Skip lines with invalid analytic_distribution
#                         continue
#
#             line_ids = filtered_line_ids
#         else:
#             # If no analytic filter, show all lines
#             line_ids = all_lines.ids
#
#         # Apply display account filter
#         if self.display_account == 'movement' and line_ids:
#             lines = self.env['account.move.line'].browse(line_ids)
#             line_ids = [l.id for l in lines if l.debit != 0 or l.credit != 0]
#
#         if not line_ids:
#             # Build helpful error message
#             error_msg = _('No journal entries found for the selected criteria.\n\nPlease check:')
#             error_details = []
#             error_details.append(f'- Date range: {self.date_from} to {self.date_to}')
#             if self.account_ids:
#                 error_details.append(f'- Accounts: {", ".join(self.account_ids.mapped("code"))}')
#             if self.journal_ids:
#                 error_details.append(f'- Journals: {", ".join(self.journal_ids.mapped("name"))}')
#             if self.analytic_account_ids:
#                 error_details.append(f'- Analytic Accounts: {", ".join(self.analytic_account_ids.mapped("name"))}')
#             error_details.append('- Make sure journal entries have analytic distribution assigned')
#
#             raise UserError(error_msg + '\n' + '\n'.join(error_details))
#
#         # Build context with analytic account names for display
#         context = {
#             'search_default_group_by_account': 1,
#         }
#
#         # Build a descriptive name
#         title = _('General Ledger Details')
#         title_parts = []
#
#         if self.account_ids:
#             account_names = ', '.join(self.account_ids.mapped('code'))
#             title_parts.append(account_names)
#
#         if self.analytic_account_ids:
#             analytic_names = ', '.join(self.analytic_account_ids.mapped('name'))
#             title_parts.append(f'Analytic: {analytic_names}')
#
#         if title_parts:
#             title += ' - ' + ' | '.join(title_parts)
#
#         return {
#             'name': title,
#             'type': 'ir.actions.act_window',
#             'res_model': 'account.move.line',
#             'view_mode': 'list',
#             'view_id': self.env.ref('analytic_general_ledger.view_general_ledger_analytic_line_tree').id,
#             'domain': [('id', 'in', line_ids)],
#             'context': context,
#             'target': 'current',
#         }
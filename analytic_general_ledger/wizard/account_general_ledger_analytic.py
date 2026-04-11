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
        Query account.move.line joined with account.payment to get
        manual_currency_exchange_rate and return rows with converted amounts.
        """
        cr = self.env.cr

        domain_parts = [
            "l.date >= %s",
            "l.date <= %s",
            "m.state = 'posted'",
        ]
        params = [self.date_from, self.date_to]

        if self.account_ids:
            domain_parts.append("l.account_id IN %s")
            params.append(tuple(self.account_ids.ids))

        if self.journal_ids:
            domain_parts.append("l.journal_id IN %s")
            params.append(tuple(self.journal_ids.ids))

        if self.target_move == 'posted':
            # already added above
            pass

        where = " AND ".join(domain_parts)

        # Analytic filter
        analytic_filter = ""
        if self.analytic_account_ids:
            conditions = [
                f"l.analytic_distribution LIKE '%%\"{aid}\"%%'"
                for aid in self.analytic_account_ids.ids
            ]
            analytic_filter = " AND (" + " OR ".join(conditions) + ")"

        sql = f"""
            SELECT
                l.id AS lid,
                l.date AS ldate,
                m.name AS move_name,
                m.id AS move_id,
                j.code AS journal_code,
                acc.account_code AS account_code,
                acc.name AS account_name,
                l.analytic_distribution,
                p.name AS partner_name,
                l.name AS label,
                COALESCE(l.debit, 0.0) AS debit,
                COALESCE(l.credit, 0.0) AS credit,
                COALESCE(l.debit, 0.0) - COALESCE(l.credit, 0.0) AS balance,
                COALESCE(pay.manual_currency_exchange_rate, 0.0) AS rate,
                pay.currency_id AS payment_currency_id,
                comp.currency_id AS company_currency_id
            FROM account_move_line l
            JOIN account_move m ON l.move_id = m.id
            JOIN account_journal j ON l.journal_id = j.id
            JOIN account_account acc ON l.account_id = acc.id
            LEFT JOIN res_partner p ON l.partner_id = p.id
            LEFT JOIN account_payment pay ON pay.move_id = m.id
            LEFT JOIN res_company comp ON m.company_id = comp.id
            WHERE {where} {analytic_filter}
            ORDER BY acc.account_code, l.date, l.id
        """

        cr.execute(sql, params)
        rows = cr.dictfetchall()

        # Apply manual exchange rate conversion
        for row in rows:
            rate = row.get('rate', 0.0)
            pay_cur = row.get('payment_currency_id')
            comp_cur = row.get('company_currency_id')
            if rate and rate > 0.0 and pay_cur and comp_cur and pay_cur != comp_cur:
                row['debit'] = row['debit'] * rate
                row['credit'] = row['credit'] * rate
                row['balance'] = row['balance'] * rate

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
                'move_name': row['move_name'] or '',
                'journal_code': row['journal_code'] or '',
                'account_code': row['account_code'] or '',
                'account_name': row['account_name'] or '',
                'analytic_distribution': str(row.get('analytic_distribution') or ''),
                'partner_name': row['partner_name'] or '',
                'label': row['label'] or '',
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
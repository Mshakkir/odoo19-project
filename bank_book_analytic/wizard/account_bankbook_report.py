from odoo import fields, models, api, _


class AccountBankBookReportAnalytic(models.TransientModel):
    _inherit = "account.bankbook.report"

    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        'bankbook_analytic_account_rel',
        'report_id',
        'analytic_account_id',
        string='Analytic Accounts',
        help='Filter by analytic accounts. Leave empty for all accounts.'
    )

    report_type = fields.Selection([
        ('combined', 'Combined Report'),
        ('separate', 'Separate by Analytic Account'),
    ], string='Report Type', required=True, default='combined',
        help='Combined: Single report with all transactions\n'
             'Separate: One report section per analytic account')

    show_without_analytic = fields.Boolean(
        string='Include Transactions Without Analytic Account',
        default=True,
        help='When separating by analytic account, also show transactions '
             'that have no analytic account assigned'
    )

    partner_ids = fields.Many2many(
        'res.partner',
        'bankbook_partner_rel',
        'report_id',
        'partner_id',
        string='Partners',
        help='Filter by partners (customers/vendors). Leave empty for all partners.'
    )

    def _build_comparison_context(self, data):
        result = super()._build_comparison_context(data)
        result['analytic_account_ids'] = data['form'].get('analytic_account_ids', [])
        result['report_type'] = data['form'].get('report_type', 'combined')
        result['show_without_analytic'] = data['form'].get('show_without_analytic', True)

        # Store partner_ids as list (serializable for reports)
        partner_ids = data['form'].get('partner_ids', [])
        if partner_ids:
            # If it's a recordset, get the IDs
            if hasattr(partner_ids, 'ids'):
                partner_ids = partner_ids.ids
        result['partner_ids'] = partner_ids or []

        return result

    def check_report(self):
        data = {}
        data['form'] = self.read([
            'target_move', 'date_from', 'date_to', 'journal_ids',
            'account_ids', 'initial_balance', 'display_account',
            'analytic_account_ids', 'report_type', 'show_without_analytic',
            'partner_ids'
        ])[0]

        comparison_context = self._build_comparison_context(data)
        data['form']['comparison_context'] = comparison_context

        return self.env.ref(
            'bank_book_analytic.action_report_bankbook_analytic'
        ).report_action(self, data=data)

    def _get_memo_for_move(self, move_id):
        """Fetch memo_new from account.payment linked to the given account.move id."""
        if not move_id:
            return ''
        payment = self.env['account.payment'].search(
            [('move_id', '=', move_id)], limit=1
        )
        if payment and payment.memo_new:
            return payment.memo_new
        return ''

    def action_show_details(self):
        """Open a new window showing bank book details"""
        self.ensure_one()

        # Get the data similar to check_report
        data = {}
        data['form'] = self.read([
            'target_move', 'date_from', 'date_to', 'journal_ids',
            'account_ids', 'initial_balance', 'display_account',
            'analytic_account_ids', 'report_type', 'show_without_analytic',
            'partner_ids'
        ])[0]

        comparison_context = self._build_comparison_context(data)

        # Get account move entries
        accounts = self.env['account.account'].browse(data['form']['account_ids'])
        if not accounts:
            journals = self.env['account.journal'].search([('type', '=', 'bank')])
            accounts = self.env['account.account']
            for journal in journals:
                for acc_out in journal.outbound_payment_method_line_ids:
                    if acc_out.payment_account_id:
                        accounts += acc_out.payment_account_id
                for acc_in in journal.inbound_payment_method_line_ids:
                    if acc_in.payment_account_id:
                        accounts += acc_in.payment_account_id

        # Get report object
        report_obj = self.env['report.bank_book_analytic.report_bankbook_analytic']
        account_res = report_obj.with_context(comparison_context)._get_account_move_entry(
            accounts,
            data['form']['initial_balance'],
            'sort_date',  # Always use date sorting
            data['form']['display_account']
        )

        # Create detail account records
        detail_accounts = []
        total_debit = 0.0
        total_credit = 0.0
        total_balance = 0.0

        for account in account_res:
            # Create lines for this account
            detail_lines = []
            account_debit = 0.0
            account_credit = 0.0
            account_balance = 0.0

            for line in account.get('move_lines', []):
                if line.get('lname') != 'Initial Balance':  # Skip initial balance lines
                    move_id = line.get('move_id', False)
                    # Fetch memo from linked payment
                    memo_value = self._get_memo_for_move(move_id)

                    detail_lines.append((0, 0, {
                        'date': line.get('ldate'),
                        'reference': line.get('move_name') or '',
                        'memo': memo_value,  # NEW: memo_new from account.payment
                        'description': line.get('lname') or '',
                        'journal_code': line.get('lcode'),
                        'partner_name': line.get('partner_name') or '',
                        'move_name': line.get('move_name') or '',
                        'label': line.get('lname') or '',
                        'debit': line.get('debit', 0.0),
                        'credit': line.get('credit', 0.0),
                        'balance': line.get('balance', 0.0),
                        'analytic_account_names': line.get('analytic_account_names') or '',
                        'move_id': move_id,
                    }))
                    account_debit += line.get('debit', 0.0)
                    account_credit += line.get('credit', 0.0)
                    account_balance = line.get('balance', 0.0)

            # Create account record with its lines
            detail_accounts.append((0, 0, {
                'account_code': account.get('code'),
                'account_name': account.get('name'),
                'line_ids': detail_lines,
                'subtotal_debit': account_debit,
                'subtotal_credit': account_credit,
                'subtotal_balance': account_debit - account_credit,  # Net = Debit - Credit
            }))

            total_debit += account_debit
            total_credit += account_credit

        # Net balance = total debit - total credit across all accounts
        total_balance = total_debit - total_credit

        # Create the details record
        details = self.env['account.bankbook.details'].create({
            'wizard_id': self.id,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'report_type': self.report_type,
            'account_ids': detail_accounts,
            'total_debit': total_debit,
            'total_credit': total_credit,
            'total_balance': total_balance,
        })

        return {
            'name': _('Bank Book Report - Detailed View'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.bankbook.details',
            'views': [(self.env.ref('bank_book_analytic.view_account_bankbook_details_form').id, 'form')],
            'res_id': details.id,
            'target': 'current',
            'context': self.env.context,
        }

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

    def _build_comparison_context(self, data):
        result = super()._build_comparison_context(data)
        result['analytic_account_ids'] = data['form'].get('analytic_account_ids', [])
        result['report_type'] = data['form'].get('report_type', 'combined')
        result['show_without_analytic'] = data['form'].get('show_without_analytic', True)
        return result

    def check_report(self):
        data = {}
        data['form'] = self.read([
            'target_move', 'date_from', 'date_to', 'journal_ids',
            'account_ids', 'sortby', 'initial_balance', 'display_account',
            'analytic_account_ids', 'report_type', 'show_without_analytic'
        ])[0]

        comparison_context = self._build_comparison_context(data)
        data['form']['comparison_context'] = comparison_context

        return self.env.ref(
            'bank_book_analytic.action_report_bankbook_analytic'
        ).report_action(self, data=data)

    def action_show_details(self):
        """Open a new window showing bank book details"""
        self.ensure_one()

        # Get the data similar to check_report
        data = {}
        data['form'] = self.read([
            'target_move', 'date_from', 'date_to', 'journal_ids',
            'account_ids', 'sortby', 'initial_balance', 'display_account',
            'analytic_account_ids', 'report_type', 'show_without_analytic'
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
            data['form']['sortby'],
            data['form']['display_account']
        )

        # Create detail account records
        detail_accounts = []
        for account in account_res:
            # Create lines for this account
            detail_lines = []
            for line in account.get('move_lines', []):
                if line.get('lname') != 'Initial Balance':  # Skip initial balance lines
                    detail_lines.append((0, 0, {
                        'date': line.get('ldate'),
                        'reference': line.get('move_name') or '',
                        'description': line.get('lname') or '',
                        'journal_code': line.get('lcode'),
                        'partner_name': line.get('partner_name') or '',
                        'move_name': line.get('move_name') or '',
                        'label': line.get('lname') or '',
                        'debit': line.get('debit', 0.0),
                        'credit': line.get('credit', 0.0),
                        'balance': line.get('balance', 0.0),
                        'analytic_account_names': line.get('analytic_account_names') or '',
                    }))

            # Create account record with its lines
            detail_accounts.append((0, 0, {
                'account_code': account.get('code'),
                'account_name': account.get('name'),
                'line_ids': detail_lines,
            }))

        # Create the details record
        details = self.env['account.bankbook.details'].create({
            'wizard_id': self.id,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'report_type': self.report_type,
            'account_ids': detail_accounts,
        })

        return {
            'name': _('Bank Book Report - Detailed View'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.bankbook.details',
            'views': [(self.env.ref('bank_book_analytic.view_account_bankbook_details_form').id, 'form')],
            'res_id': details.id,
            'target': 'new',
            'context': dict(self.env.context, dialog_size='extra-large'),
        }






# from odoo import fields, models, api
#
#
# class AccountBankBookDetails(models.TransientModel):
#     _name = 'account.bankbook.details'
#     _description = 'Bank Book Details'
#
#     wizard_id = fields.Many2one('account.bankbook.report', string='Wizard', ondelete='cascade')
#     date_from = fields.Date(string='Date From', readonly=True)
#     date_to = fields.Date(string='Date To', readonly=True)
#     report_type = fields.Selection([
#         ('combined', 'Combined Report'),
#         ('separate', 'Separate by Analytic Account'),
#     ], string='Report Type', readonly=True)
#     account_ids = fields.One2many('account.bankbook.details.account', 'details_id', string='Bank Accounts')
#     total_debit = fields.Float(string='Total Debit', compute='_compute_totals')
#     total_credit = fields.Float(string='Total Credit', compute='_compute_totals')
#     total_balance = fields.Float(string='Total Balance', compute='_compute_totals')
#
#     @api.depends('account_ids.subtotal_debit', 'account_ids.subtotal_credit', 'account_ids.subtotal_balance')
#     def _compute_totals(self):
#         for record in self:
#             record.total_debit = sum(record.account_ids.mapped('subtotal_debit'))
#             record.total_credit = sum(record.account_ids.mapped('subtotal_credit'))
#             record.total_balance = sum(record.account_ids.mapped('subtotal_balance'))
#
#
# class AccountBankBookDetailsAccount(models.TransientModel):
#     _name = 'account.bankbook.details.account'
#     _description = 'Bank Book Details Account'
#     _order = 'account_code'
#
#     details_id = fields.Many2one('account.bankbook.details', string='Details', required=True, ondelete='cascade')
#     account_code = fields.Char(string='Account Code', readonly=True)
#     account_name = fields.Char(string='Account Name', readonly=True)
#     line_ids = fields.One2many('account.bankbook.details.line', 'account_id', string='Transactions')
#     subtotal_debit = fields.Float(string='Subtotal Debit', compute='_compute_subtotals')
#     subtotal_credit = fields.Float(string='Subtotal Credit', compute='_compute_subtotals')
#     subtotal_balance = fields.Float(string='Subtotal Balance', compute='_compute_subtotals')
#
#     @api.depends('line_ids.debit', 'line_ids.credit', 'line_ids.balance')
#     def _compute_subtotals(self):
#         for record in self:
#             record.subtotal_debit = sum(record.line_ids.mapped('debit'))
#             record.subtotal_credit = sum(record.line_ids.mapped('credit'))
#             # Balance should be debit - credit
#             record.subtotal_balance = record.subtotal_debit - record.subtotal_credit
#
#     def action_view_transactions(self):
#         """Open form view showing all transactions for this bank account"""
#         self.ensure_one()
#         return {
#             'name': f'{self.account_code} - {self.account_name}',
#             'type': 'ir.actions.act_window',
#             'res_model': 'account.bankbook.details.account',
#             'view_mode': 'form',
#             'res_id': self.id,
#             'target': 'new',
#             'context': self.env.context,
#         }
#
#
# class AccountBankBookDetailsLine(models.TransientModel):
#     _name = 'account.bankbook.details.line'
#     _description = 'Bank Book Details Line'
#     _order = 'date, id'
#
#     account_id = fields.Many2one('account.bankbook.details.account', string='Account', required=True, ondelete='cascade')
#     date = fields.Date(string='Date', readonly=True)
#     reference = fields.Char(string='Reference', readonly=True)
#     description = fields.Char(string='Description', readonly=True)
#     journal_code = fields.Char(string='Journal', readonly=True)
#     partner_name = fields.Char(string='Partner', readonly=True)
#     move_name = fields.Char(string='Entry', readonly=True)
#     label = fields.Char(string='Label', readonly=True)
#     debit = fields.Float(string='Debit', readonly=True, digits=(16, 2))
#     credit = fields.Float(string='Credit', readonly=True, digits=(16, 2))
#     balance = fields.Float(string='Balance', readonly=True, digits=(16, 2))
#     analytic_account_names = fields.Char(string='Analytic Accounts', readonly=True)

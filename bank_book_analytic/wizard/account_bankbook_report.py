from odoo import fields, models, api, _, logging

_logger = logging.getLogger(__name__)


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
        help='Combined: Single report with all transactions\\n'
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
        """Print button - generates PDF with bank totals only"""
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

    def show_details(self):
        """Show Details button - opens new window with detailed view"""
        self.ensure_one()

        # Create the details wizard record with data
        detail_wizard = self.env['bank.book.details.wizard'].create({
            'date_from': self.date_from,
            'date_to': self.date_to,
            'journal_ids': [(6, 0, self.journal_ids.ids)],
            'account_ids': [(6, 0, self.account_ids.ids)],
            'analytic_account_ids': [(6, 0, self.analytic_account_ids.ids)],
            'report_type': self.report_type,
            'show_without_analytic': self.show_without_analytic,
            'target_move': self.target_move,
            'sortby': self.sortby,
            'initial_balance': self.initial_balance,
            'display_account': self.display_account,
        })

        # Fetch and populate detail lines
        detail_wizard._fetch_details()

        return {
            'type': 'ir.actions.act_window',
            'name': 'Bank Book Details',
            'res_model': 'bank.book.details.wizard',
            'res_id': detail_wizard.id,
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'views': [(False, 'form')],
        }


class BankBookDetailsWizard(models.TransientModel):
    _name = 'bank.book.details.wizard'
    _description = 'Bank Book Details View'

    date_from = fields.Date('Start Date')
    date_to = fields.Date('End Date')
    journal_ids = fields.Many2many('account.journal')
    account_ids = fields.Many2many('account.account')
    analytic_account_ids = fields.Many2many('account.analytic.account')
    report_type = fields.Selection([
        ('combined', 'Combined Report'),
        ('separate', 'Separate by Analytic Account'),
    ])
    show_without_analytic = fields.Boolean()
    target_move = fields.Selection([
        ('posted', 'Posted Entries'),
        ('all', 'All Entries'),
    ])
    sortby = fields.Selection([
        ('sort_date', 'Date'),
        ('sort_journal_partner', 'Journal & Partner'),
    ])
    initial_balance = fields.Boolean()
    display_account = fields.Selection([
        ('all', 'All'),
        ('movement', 'With Movements'),
        ('not_zero', 'With Balance'),
    ])

    # Store the detailed data
    detail_line_ids = fields.One2many(
        'bank.book.detail.line',
        'wizard_id',
        string='Details'
    )

    def _fetch_details(self):
        """Fetch bank book details"""
        report = self.env['report.bank_book_analytic.report_bankbook_analytic']

        # Prepare data dictionary
        data = {
            'form': {
                'date_from': self.date_from,
                'date_to': self.date_to,
                'journal_ids': self.journal_ids.ids or [],
                'account_ids': self.account_ids.ids or [],
                'analytic_account_ids': self.analytic_account_ids.ids or [],
                'report_type': self.report_type,
                'show_without_analytic': self.show_without_analytic,
                'target_move': self.target_move,
                'sortby': self.sortby,
                'initial_balance': self.initial_balance,
                'display_account': self.display_account,
            }
        }

        try:
            # Get report values
            report_values = report._get_report_values([], data=data)
            accounts = report_values.get('Accounts', [])

            detail_lines = []
            line_seq = 1

            for account in accounts:
                for move_line in account.get('move_lines', []):
                    detail_lines.append((0, 0, {
                        'sequence': line_seq,
                        'date': move_line.get('ldate'),
                        'reference': move_line.get('lref'),
                        'description': move_line.get('lname'),
                        'journal': move_line.get('lcode'),
                        'account_code': account.get('code'),
                        'account_name': account.get('name'),
                        'debit': move_line.get('debit', 0),
                        'credit': move_line.get('credit', 0),
                        'balance': move_line.get('balance', 0),
                        'analytic_accounts': move_line.get('analytic_account_names', ''),
                    }))
                    line_seq += 1

            self.detail_line_ids = detail_lines
        except Exception as e:
            _logger.error(f"Error fetching bank book details: {str(e)}")


class BankBookDetailLine(models.TransientModel):
    _name = 'bank.book.detail.line'
    _description = 'Bank Book Detail Line'

    wizard_id = fields.Many2one('bank.book.details.wizard')
    sequence = fields.Integer('Seq')
    date = fields.Date('Date')
    reference = fields.Char('Reference')
    description = fields.Char('Description')
    journal = fields.Char('Journal')
    account_code = fields.Char('Account Code')
    account_name = fields.Char('Account Name')
    debit = fields.Float('Debit')
    credit = fields.Float('Credit')
    balance = fields.Float('Balance')
    analytic_accounts = fields.Char('Analytic Accounts')














# from odoo import fields, models, api, _
#
#
# class AccountBankBookReportAnalytic(models.TransientModel):
#     _inherit = "account.bankbook.report"
#
#     analytic_account_ids = fields.Many2many(
#         'account.analytic.account',
#         'bankbook_analytic_account_rel',
#         'report_id',
#         'analytic_account_id',
#         string='Analytic Accounts',
#         help='Filter by analytic accounts. Leave empty for all accounts.'
#     )
#
#     report_type = fields.Selection([
#         ('combined', 'Combined Report'),
#         ('separate', 'Separate by Analytic Account'),
#     ], string='Report Type', required=True, default='combined',
#         help='Combined: Single report with all transactions\\n'
#              'Separate: One report section per analytic account')
#
#     show_without_analytic = fields.Boolean(
#         string='Include Transactions Without Analytic Account',
#         default=True,
#         help='When separating by analytic account, also show transactions '
#              'that have no analytic account assigned'
#     )
#
#     def _build_comparison_context(self, data):
#         result = super()._build_comparison_context(data)
#         result['analytic_account_ids'] = data['form'].get('analytic_account_ids', [])
#         result['report_type'] = data['form'].get('report_type', 'combined')
#         result['show_without_analytic'] = data['form'].get('show_without_analytic', True)
#         return result
#
#     def check_report(self):
#         data = {}
#         data['form'] = self.read([
#             'target_move', 'date_from', 'date_to', 'journal_ids',
#             'account_ids', 'sortby', 'initial_balance', 'display_account',
#             'analytic_account_ids', 'report_type', 'show_without_analytic'
#         ])[0]
#
#         comparison_context = self._build_comparison_context(data)
#         data['form']['comparison_context'] = comparison_context
#
#         return self.env.ref(
#             'bank_book_analytic.action_report_bankbook_analytic'
#         ).report_action(self, data=data)
#
#
#
#
#
#
#
#
#
#

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

        # Create detail lines
        detail_lines = []
        for account in account_res:
            for line in account.get('move_lines', []):
                if line.get('lname') != 'Initial Balance':  # Skip initial balance lines
                    detail_lines.append((0, 0, {
                        'account_code': account.get('code'),
                        'account_name': account.get('name'),
                        'date': line.get('ldate'),
                        'journal_code': line.get('lcode'),
                        'partner_name': line.get('partner_name') or '',
                        'move_name': line.get('move_name') or '',
                        'label': line.get('lname') or '',
                        'debit': line.get('debit', 0.0),
                        'credit': line.get('credit', 0.0),
                        'balance': line.get('balance', 0.0),
                        'analytic_account_names': line.get('analytic_account_names') or '',
                    }))

        # Create the details record
        details = self.env['account.bankbook.details'].create({
            'wizard_id': self.id,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'report_type': self.report_type,
            'line_ids': detail_lines,
        })

        return {
            'name': _('Bank Book Details'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.bankbook.details',
            'view_mode': 'form',
            'res_id': details.id,
            'target': 'new',
            'context': self.env.context,
        }









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

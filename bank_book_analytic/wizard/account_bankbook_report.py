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
#             'bank_book_analytic.action_report_bank_book_analytic'
#         ).report_action(self, data=data)
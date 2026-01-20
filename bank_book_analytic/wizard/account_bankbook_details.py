from odoo import fields, models, api


class AccountBankBookDetails(models.TransientModel):
    _name = 'account.bankbook.details'
    _description = 'Bank Book Details'

    wizard_id = fields.Many2one('account.bankbook.report', string='Wizard', ondelete='cascade')
    date_from = fields.Date(string='Date From', readonly=True)
    date_to = fields.Date(string='Date To', readonly=True)
    report_type = fields.Selection([
        ('combined', 'Combined Report'),
        ('separate', 'Separate by Analytic Account'),
    ], string='Report Type', readonly=True)
    account_ids = fields.One2many('account.bankbook.details.account', 'details_id', string='Bank Accounts')
    total_debit = fields.Float(string='Total Debit', compute='_compute_totals')
    total_credit = fields.Float(string='Total Credit', compute='_compute_totals')
    total_balance = fields.Float(string='Total Balance', compute='_compute_totals')

    @api.depends('account_ids.subtotal_debit', 'account_ids.subtotal_credit', 'account_ids.subtotal_balance')
    def _compute_totals(self):
        for record in self:
            record.total_debit = sum(record.account_ids.mapped('subtotal_debit'))
            record.total_credit = sum(record.account_ids.mapped('credit'))
            record.total_balance = sum(record.account_ids.mapped('subtotal_balance'))


class AccountBankBookDetailsAccount(models.TransientModel):
    _name = 'account.bankbook.details.account'
    _description = 'Bank Book Details Account'
    _order = 'account_code'

    details_id = fields.Many2one('account.bankbook.details', string='Details', required=True, ondelete='cascade')
    account_code = fields.Char(string='Account Code', readonly=True)
    account_name = fields.Char(string='Account Name', readonly=True)
    line_ids = fields.One2many('account.bankbook.details.line', 'account_id', string='Transactions')
    subtotal_debit = fields.Float(string='Subtotal Debit', compute='_compute_subtotals')
    subtotal_credit = fields.Float(string='Subtotal Credit', compute='_compute_subtotals')
    subtotal_balance = fields.Float(string='Subtotal Balance', compute='_compute_subtotals')

    @api.depends('line_ids.debit', 'line_ids.credit', 'line_ids.balance')
    def _compute_subtotals(self):
        for record in self:
            record.subtotal_debit = sum(record.line_ids.mapped('debit'))
            record.subtotal_credit = sum(record.line_ids.mapped('credit'))
            # Balance should be debit - credit
            record.subtotal_balance = record.subtotal_debit - record.subtotal_credit

    def action_view_transactions(self):
        """Open form view showing all transactions for this bank account"""
        self.ensure_one()
        return {
            'name': f'{self.account_code} - {self.account_name}',
            'type': 'ir.actions.act_window',
            'res_model': 'account.bankbook.details.account',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': self.env.context,
        }


class AccountBankBookDetailsLine(models.TransientModel):
    _name = 'account.bankbook.details.line'
    _description = 'Bank Book Details Line'
    _order = 'date, id'

    account_id = fields.Many2one('account.bankbook.details.account', string='Account', required=True, ondelete='cascade')
    date = fields.Date(string='Date', readonly=True)
    reference = fields.Char(string='Reference', readonly=True)
    description = fields.Char(string='Description', readonly=True)
    journal_code = fields.Char(string='Journal', readonly=True)
    partner_name = fields.Char(string='Partner', readonly=True)
    move_name = fields.Char(string='Entry', readonly=True)
    label = fields.Char(string='Label', readonly=True)
    debit = fields.Float(string='Debit', readonly=True, digits=(16, 2))
    credit = fields.Float(string='Credit', readonly=True, digits=(16, 2))
    balance = fields.Float(string='Balance', readonly=True, digits=(16, 2))
    analytic_account_names = fields.Char(string='Analytic Accounts', readonly=True)















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
#             # Balance should be the last line's balance
#             if record.line_ids:
#                 sorted_lines = record.line_ids.sorted(key=lambda l: (l.date or '', l.id))
#                 record.subtotal_balance = sorted_lines[-1].balance if sorted_lines else 0.0
#             else:
#                 record.subtotal_balance = 0.0
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
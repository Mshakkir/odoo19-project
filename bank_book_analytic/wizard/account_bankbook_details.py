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
    line_ids = fields.One2many('account.bankbook.details.line', 'details_id', string='Details Lines')
    total_debit = fields.Float(string='Total Debit', compute='_compute_totals', store=False)
    total_credit = fields.Float(string='Total Credit', compute='_compute_totals', store=False)
    total_balance = fields.Float(string='Total Balance', compute='_compute_totals', store=False)

    @api.depends('line_ids.debit', 'line_ids.credit', 'line_ids.balance')
    def _compute_totals(self):
        for record in self:
            record.total_debit = sum(record.line_ids.mapped('debit'))
            record.total_credit = sum(record.line_ids.mapped('credit'))
            record.total_balance = sum(record.line_ids.mapped('balance'))


class AccountBankBookDetailsLine(models.TransientModel):
    _name = 'account.bankbook.details.line'
    _description = 'Bank Book Details Line'
    _order = 'date, id'

    details_id = fields.Many2one('account.bankbook.details', string='Details', ondelete='cascade')
    account_code = fields.Char(string='Account Code', readonly=True)
    account_name = fields.Char(string='Account Name', readonly=True)
    date = fields.Date(string='Date', readonly=True)
    journal_code = fields.Char(string='Journal', readonly=True)
    partner_name = fields.Char(string='Partner', readonly=True)
    move_name = fields.Char(string='Entry', readonly=True)
    label = fields.Char(string='Label', readonly=True)
    debit = fields.Float(string='Debit', readonly=True)
    credit = fields.Float(string='Credit', readonly=True)
    balance = fields.Float(string='Balance', readonly=True)
    analytic_account_names = fields.Char(string='Analytic Accounts', readonly=True)
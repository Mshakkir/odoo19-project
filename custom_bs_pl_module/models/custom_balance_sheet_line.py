from odoo import models, fields, api

class CustomBalanceSheetLine(models.TransientModel):
    _name = 'custom.balance.sheet.line'
    _description = 'Custom Balance Sheet Line'
    _order = 'account_type, name'

    name = fields.Char(string='Account', required=True)
    account_id = fields.Many2one('account.account', string='Account Ref', readonly=True)

    # Use Char instead of Selection to allow dynamic account type values (e.g. 'asset_cash', 'asset_fixed')
    account_type = fields.Char(string='Type', readonly=True)

    debit = fields.Monetary(string='Debit', currency_field='currency_id', readonly=True)
    credit = fields.Monetary(string='Credit', currency_field='currency_id', readonly=True)
    balance = fields.Monetary(string='Balance', currency_field='currency_id', readonly=True)

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        readonly=True
    )

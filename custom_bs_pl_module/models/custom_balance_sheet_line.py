from odoo import models, fields

class CustomBalanceSheetLine(models.TransientModel):
    _name = 'custom.balance.sheet.line'
    _description = 'Custom Balance Sheet Line'

    name = fields.Char(string='Account')
    account_id = fields.Many2one('account.account', string='Account Ref')
    debit = fields.Monetary(string='Debit', currency_field='currency_id')
    credit = fields.Monetary(string='Credit', currency_field='currency_id')
    balance = fields.Monetary(string='Balance', currency_field='currency_id')
    account_type = fields.Char(string='Type')  # 'Asset' or 'Liability'
    currency_id = fields.Many2one('res.currency', string='Currency')

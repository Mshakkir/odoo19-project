from odoo import fields, models

class BalanceSheetLine(models.TransientModel):
    _name = "custom.balance.sheet.line"
    _description = "Balance Sheet Line"

    account_id = fields.Many2one('account.account', string='Account')
    debit = fields.Float(string='Debit')
    credit = fields.Float(string='Credit')
    balance = fields.Float(string='Balance')
    category = fields.Selection([
        ('asset', 'Asset'),
        ('liability', 'Liability'),
    ], string='Category')

    def action_view_ledger(self):
        """Open ledger for selected account"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Ledger Entries',
            'res_model': 'account.move.line',
            'view_mode': 'list,form',
            'domain': [('account_id', '=', self.account_id.id)],
            'target': 'current',
        }

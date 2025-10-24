from odoo import models, fields

class CustomBalanceSheetLine(models.TransientModel):
    _name = 'custom.balance.sheet.line'
    _description = 'Custom Balance Sheet Line'
    _order = 'account_type, name'

    name = fields.Char(string='Account', required=True)
    account_id = fields.Many2one('account.account', string='Account')  # 👈 Added this
    account_type = fields.Char(string='Type', readonly=True)
    debit = fields.Monetary(string='Debit', currency_field='currency_id', readonly=True)
    credit = fields.Monetary(string='Credit', currency_field='currency_id', readonly=True)
    balance = fields.Monetary(string='Balance', currency_field='currency_id', readonly=True)

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        readonly=True,
    )

    def action_view_ledger(self):
        """Open general ledger entries for the account"""
        self.ensure_one()
        if not self.account_id:
            return False
        action = self.env.ref('account.action_move_line_select').read()[0]
        action['domain'] = [('account_id', '=', self.account_id.id)]
        return action

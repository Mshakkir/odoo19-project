from odoo import models, fields

class TrialBalanceLine(models.TransientModel):
    _name = 'trial.balance.line'
    _description = 'Trial Balance Line'

    wizard_id = fields.Many2one('trial.balance.wizard')
    account_id = fields.Many2one('account.account', string='Account')
    opening_balance = fields.Monetary(string='Opening')
    debit = fields.Monetary(string='Debit')
    credit = fields.Monetary(string='Credit')
    ending_balance = fields.Monetary(string='Ending')

    move_line_ids = fields.Many2many('account.move.line', string='Entries')

    def open_entries(self):
        self.ensure_one()
        return {
            'name': 'Journal Items',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.move_line_ids.ids)],
            'target': 'current',
        }

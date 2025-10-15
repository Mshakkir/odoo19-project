# models/tb_line.py
from odoo import models, fields

class TrialBalanceLine(models.TransientModel):
    _name = 'trial.balance.line'
    _description = 'Trial Balance Line'

    wizard_id = fields.Many2one('trial.balance.wizard', string='Wizard')
    account_id = fields.Many2one('account.account', string='Account')

    # currency field required for Monetary fields
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id.id
    )

    opening_balance = fields.Monetary(string='Opening', currency_field='currency_id')
    debit = fields.Monetary(string='Debit', currency_field='currency_id')
    credit = fields.Monetary(string='Credit', currency_field='currency_id')
    ending_balance = fields.Monetary(string='Ending', currency_field='currency_id')

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

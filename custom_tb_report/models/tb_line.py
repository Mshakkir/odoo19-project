from odoo import models, fields

class TrialBalanceLine(models.TransientModel):
    _name = 'trial.balance.line'
    _description = 'Trial Balance Detail Line'

    wizard_id = fields.Many2one('account.trial.balance.report.wizard', ondelete='cascade')
    account_id = fields.Many2one('account.account', string='Account')
    opening_balance = fields.Float(string='Opening Balance')
    debit = fields.Float(string='Debit')
    credit = fields.Float(string='Credit')
    ending_balance = fields.Float(string='Ending Balance')

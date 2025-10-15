# models/trial_balance_line.py
from odoo import models, fields

class TrialBalanceLine(models.Model):
    _name = 'trial.balance.line'
    _description = 'Trial Balance Line'

    wizard_id = fields.Many2one('account.balance.report', string='Wizard')
    account_id = fields.Many2one('account.account', string='Account')
    opening_balance = fields.Monetary(string='Opening Balance', currency_field='company_currency_id')
    debit = fields.Monetary(string='Debit', currency_field='company_currency_id')
    credit = fields.Monetary(string='Credit', currency_field='company_currency_id')
    ending_balance = fields.Monetary(string='Ending Balance', currency_field='company_currency_id')
    company_currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

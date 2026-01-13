# from odoo import models, fields
#
# class TrialBalanceLine(models.TransientModel):
#     _name = 'trial.balance.line'
#     _description = 'Trial Balance Line'
#
#     wizard_id = fields.Many2one('account.balance.report', string='Wizard')
#     account_id = fields.Many2one('account.account', string='Account')
#     opening_balance = fields.Monetary(string='Opening Balance', currency_field='company_currency_id')
#     debit = fields.Monetary(string='Debit', currency_field='company_currency_id')
#     credit = fields.Monetary(string='Credit', currency_field='company_currency_id')
#     ending_balance = fields.Monetary(string='Ending Balance', currency_field='company_currency_id')
#     company_currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
from odoo import models, fields, api


class TrialBalanceLine(models.TransientModel):
    _name = 'trial.balance.line'
    _description = 'Trial Balance Line'

    wizard_id = fields.Many2one('account.balance.report', string='Wizard')
    account_id = fields.Many2one('account.account', string='Account')
    opening_balance = fields.Monetary(string='Opening Balance', currency_field='company_currency_id')
    debit = fields.Monetary(string='Debit', currency_field='company_currency_id')
    credit = fields.Monetary(string='Credit', currency_field='company_currency_id')
    ending_balance = fields.Monetary(string='Ending Balance', currency_field='company_currency_id')
    company_currency_id = fields.Many2one('res.currency', string='Currency',
                                          default=lambda self: self.env.company.currency_id)
    is_total = fields.Boolean(string='Is Total Row', default=False)

    @api.model
    def calculate_totals(self, wizard_id):
        """Calculate totals for the trial balance"""
        lines = self.search([('wizard_id', '=', wizard_id), ('is_total', '=', False)])

        total_opening_debit = sum(line.opening_balance for line in lines if line.opening_balance > 0)
        total_opening_credit = abs(sum(line.opening_balance for line in lines if line.opening_balance < 0))
        total_debit = sum(lines.mapped('debit'))
        total_credit = sum(lines.mapped('credit'))
        total_ending_debit = sum(line.ending_balance for line in lines if line.ending_balance > 0)
        total_ending_credit = abs(sum(line.ending_balance for line in lines if line.ending_balance < 0))

        return {
            'opening_debit': total_opening_debit,
            'opening_credit': total_opening_credit,
            'debit': total_debit,
            'credit': total_credit,
            'ending_debit': total_ending_debit,
            'ending_credit': total_ending_credit,
        }
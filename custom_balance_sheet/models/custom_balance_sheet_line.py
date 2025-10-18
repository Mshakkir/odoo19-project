from odoo import models, fields, api, _
from datetime import date

class CustomBalanceSheetLine(models.TransientModel):
    _name = "custom.balance.sheet.line"
    _description = "Custom Balance Sheet Line"

    name = fields.Char(string="Account")
    account_id = fields.Many2one('account.account', string="Account Ref")
    debit = fields.Monetary(string="Debit", currency_field='currency_id')
    credit = fields.Monetary(string="Credit", currency_field='currency_id')
    balance = fields.Monetary(string="Balance", currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    account_type = fields.Selection([
        ('asset', 'Asset'),
        ('liability', 'Liability'),
        ('equity', 'Equity'),
        ('income', 'Income'),
        ('expense', 'Expense')
    ], string="Type")

    @api.model
    def generate_lines(self, date_from, date_to, target_moves):
        """Generate temporary lines for the wizard"""
        self.search([]).unlink()  # clear old data

        move_state = ['posted'] if target_moves == 'posted' else ['draft', 'posted']

        accounts = self.env['account.account'].search([])
        for acc in accounts:
            domain = [
                ('account_id', '=', acc.id),
                ('date', '>=', date_from),
                ('date', '<=', date_to),
                ('move_id.state', 'in', move_state)
            ]
            lines = self.env['account.move.line'].search(domain)
            debit = sum(lines.mapped('debit'))
            credit = sum(lines.mapped('credit'))
            balance = debit - credit

            if debit or credit:
                self.create({
                    'name': acc.display_name,
                    'account_id': acc.id,
                    'debit': debit,
                    'credit': credit,
                    'balance': balance,
                    'account_type': acc.account_type,
                })

    def action_view_ledger(self):
        """Open account move lines (ledger) for this account"""
        return {
            'name': _('Ledger Entries'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'tree,form',
            'domain': [('account_id', '=', self.account_id.id)],
            'context': {'create': False},
            'target': 'current',
        }

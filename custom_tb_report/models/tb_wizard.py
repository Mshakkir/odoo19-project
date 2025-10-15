from odoo import models, fields, api

class TrialBalanceWizard(models.TransientModel):
    _inherit = 'account.trial.balance.report.wizard'  # inherits Odoo Mates’ wizard

    line_ids = fields.One2many('trial.balance.line', 'wizard_id', string='Trial Balance Lines')

    def compute_trial_balance(self):
        self.ensure_one()
        TrialLine = self.env['trial.balance.line']
        self.line_ids.unlink()

        # Search all accounts
        accounts = self.env['account.account'].search([])
        for account in accounts:
            # Compute balances
            domain = [
                ('account_id', '=', account.id),
                ('date', '>=', self.date_from),
                ('date', '<=', self.date_to),
                ('move_id.state', '=', 'posted')
            ]
            move_lines = self.env['account.move.line'].search(domain)
            debit = sum(move_lines.mapped('debit'))
            credit = sum(move_lines.mapped('credit'))
            opening_balance = self._get_opening_balance(account)
            ending_balance = opening_balance + debit - credit

            TrialLine.create({
                'wizard_id': self.id,
                'account_id': account.id,
                'opening_balance': opening_balance,
                'debit': debit,
                'credit': credit,
                'ending_balance': ending_balance,
            })

    def _get_opening_balance(self, account):
        domain = [
            ('account_id', '=', account.id),
            ('date', '<', self.date_from),
            ('move_id.state', '=', 'posted')
        ]
        lines = self.env['account.move.line'].search(domain)
        return sum(lines.mapped(lambda l: l.debit - l.credit))

    def open_trial_balance_details(self):
        self.compute_trial_balance()
        return {
            'name': 'Trial Balance Summary',
            'type': 'ir.actions.act_window',
            'res_model': 'trial.balance.line',
            'view_mode': 'list,form',
            'target': 'current',
            'context': {'default_wizard_id': self.id},
            'domain': [('wizard_id', '=', self.id)],
        }

# models/tb_wizard_inherit.py
from odoo import models, fields, api

class TrialBalanceWizardInherit(models.TransientModel):
    _inherit = 'account.balance.report'  # Mates TB wizard

    line_ids = fields.One2many('trial.balance.line', 'wizard_id', string='Trial Balance Lines')

    def action_show_tb(self):
        self.compute_tb_lines()
        return {
            'name': 'Trial Balance',
            'type': 'ir.actions.act_window',
            'res_model': 'trial.balance.line',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [('wizard_id', '=', self.id)],
        }

    def compute_tb_lines(self):
        self.ensure_one()
        self.line_ids.unlink()
        accounts = self.env['account.account'].search([])  # you can filter by type/journal if needed
        for account in accounts:
            opening = self._get_opening(account)
            move_lines = account.line_ids.filtered(
                lambda l: l.date >= self.date_from and l.date <= self.date_to and l.move_id.state == 'posted'
            )
            debit = sum(move_lines.mapped('debit'))
            credit = sum(move_lines.mapped('credit'))
            ending = opening + debit - credit
            self.env['trial.balance.line'].create({
                'wizard_id': self.id,
                'account_id': account.id,
                'opening_balance': opening,
                'debit': debit,
                'credit': credit,
                'ending_balance': ending,
            })

    def _get_opening(self, account):
        lines = account.line_ids.filtered(lambda l: l.date < self.date_from and l.move_id.state == 'posted')
        return sum(lines.mapped(lambda l: l.debit - l.credit))

# models/account_balance_report_inherit.py
from odoo import models, api

class AccountBalanceReportInherit(models.TransientModel):
    _inherit = 'account.balance.report'

    def action_show_tb(self):
        self.ensure_one()

        # Remove old lines
        self.env['trial.balance.line'].search([('wizard_id', '=', self.id)]).unlink()

        accounts = self.env['account.account'].search([])
        for account in accounts:
            opening = sum(account.line_ids.filtered(
                lambda l: l.date < self.date_from and l.move_id.state == 'posted'
            ).mapped(lambda l: l.debit - l.credit))

            move_lines = account.line_ids.filtered(
                lambda l: self.date_from <= l.date <= self.date_to and l.move_id.state == 'posted'
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

        return {
            'name': 'Trial Balance',
            'type': 'ir.actions.act_window',
            'res_model': 'trial.balance.line',
            'view_mode': 'tree,form',
            'target': 'current',
            'domain': [('wizard_id', '=', self.id)],
        }

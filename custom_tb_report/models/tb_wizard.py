from odoo import models

class AccountBalanceReportInherit(models.TransientModel):
    _inherit = 'account.balance.report'  # <- inherit Trial Balance wizard

    def open_trial_balance(self):
        self.ensure_one()

        # Clear previous TB lines
        self.env['trial.balance.line'].search([('wizard_id', '=', self.id)]).unlink()

        accounts = self.env['account.account'].search([])

        for account in accounts:
            move_lines = self.env['account.move.line'].search([
                ('account_id', '=', account.id),
                ('move_id.state', '=', 'posted'),
            ])

            opening = sum(move_lines.filtered(lambda l: l.date < self.date_from).mapped(lambda l: l.debit - l.credit))
            period_lines = move_lines.filtered(lambda l: self.date_from <= l.date <= self.date_to)
            debit = sum(period_lines.mapped('debit'))
            credit = sum(period_lines.mapped('credit'))
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
            'views': [
                (self.env.ref('custom_tb_report.view_trial_balance_line_list').id, 'tree'),
                (self.env.ref('custom_tb_report.view_trial_balance_line_form').id, 'form'),
            ],
            'target': 'current',
            'domain': [('wizard_id', '=', self.id)],
        }

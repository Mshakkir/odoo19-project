from odoo import models, fields, api

class TrialBalanceWizard(models.TransientModel):
    _inherit = 'account.balance.report'
    _description = 'Trial Balance Wizard'

    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    # optional filters: journal_ids, account_type, etc.

    line_ids = fields.One2many('trial.balance.line', 'wizard_id', string='Lines')

    def compute_tb(self):
        self.ensure_one()
        self.line_ids.unlink()
        # For each account in chart of accounts:
        accounts = self.env['account.account'].search([])  # you may filter
        for account in accounts:
            # Get opening balance (before date_from)
            opening = self._get_opening(account, self.date_from)
            # Get debit/credit between date_from and date_to
            move_lines = account.line_ids.filtered(
                lambda l: l.date >= self.date_from and l.date <= self.date_to and l.move_id.state == 'posted'
            )
            total_debit = sum(move_lines.mapped('debit'))
            total_credit = sum(move_lines.mapped('credit'))
            ending = opening + total_debit - total_credit
            self.env['trial.balance.line'].create({
                'wizard_id': self.id,
                'account_id': account.id,
                'opening_balance': opening,
                'debit': total_debit,
                'credit': total_credit,
                'ending_balance': ending,
            })

    def action_show_tb(self):
        # compute then return window
        self.compute_tb()
        return {
            'name': 'Trial Balance',
            'type': 'ir.actions.act_window',
            'res_model': 'trial.balance.line',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [('wizard_id', '=', self.id)],
        }

    def _get_opening(self, account, date_from):
        # Sum all posted move lines before date_from
        lines = account.line_ids.filtered(lambda l: l.date < date_from and l.move_id.state == 'posted')
        return sum(lines.mapped(lambda l: l.debit - l.credit))

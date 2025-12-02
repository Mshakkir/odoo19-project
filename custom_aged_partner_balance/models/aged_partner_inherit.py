from odoo import models

class AccountAgedTrialBalance(models.TransientModel):
    _inherit = 'account.aged.trial.balance'

    def show_details(self):
        """Open detailed move lines window."""
        self.ensure_one()

        domain = [
            ('journal_id', 'in', self.journal_ids.ids),
            ('date', '<=', self.date_from),
        ]

        # Customer / Supplier filter
        if self.result_selection == 'customer':
            domain += [('account_id.account_type', '=', 'asset_receivable')]
        elif self.result_selection == 'supplier':
            domain += [('account_id.account_type', '=', 'liability_payable')]

        # Posted?
        if self.target_move == 'posted':
            domain += [('parent_state', '=', 'posted')]

        # If partner selected in wizard
        if self.partner_ids:
            domain += [('partner_id', 'in', self.partner_ids.ids)]

        return {
            'name': "Aged Report Details",
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'account.move.line',
            'domain': domain,
            'context': {'search_default_group_by_partner': 1},
        }

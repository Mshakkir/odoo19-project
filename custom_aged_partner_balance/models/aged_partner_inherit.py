from odoo import models, _


class AccountAgedTrialBalance(models.TransientModel):
    _inherit = 'account.aged.trial.balance'

    def show_details(self):
        """
        Show detailed journal entries based on wizard filters.
        """
        self.ensure_one()

        # Build domain based on wizard settings
        domain = [
            ('date', '<=', self.date_from),
            ('reconciled', '=', False),
        ]

        # Add journal filter
        if self.journal_ids:
            domain.append(('journal_id', 'in', self.journal_ids.ids))

        # Add partner filter
        if self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))

        # Filter by account type
        if self.result_selection == 'customer':
            domain.append(('account_id.account_type', '=', 'asset_receivable'))
            action_name = _('Aged Receivable - Journal Entries')
        elif self.result_selection == 'supplier':
            domain.append(('account_id.account_type', '=', 'liability_payable'))
            action_name = _('Aged Payable - Journal Entries')
        else:
            domain.append(('account_id.account_type', 'in', ['asset_receivable', 'liability_payable']))
            action_name = _('Aged Partner Balance - Journal Entries')

        # Filter by posted/all moves
        if self.target_move == 'posted':
            domain.append(('parent_state', '=', 'posted'))

        return {
            'name': action_name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'domain': domain,
            'view_mode': 'tree,form',
            'views': [(False, 'tree'), (False, 'form')],
            'target': 'current',
            'context': {
                'search_default_group_by_partner': 1,
            },
        }
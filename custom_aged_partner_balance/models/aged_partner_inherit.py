from odoo import models, fields

class AccountAgedTrialBalance(models.TransientModel):
    _inherit = 'account.aged.trial.balance'

    def show_details(self):
        """
        Open detailed move lines based on the wizard filters.
        Shows only unreconciled items (open invoices/bills).
        """
        self.ensure_one()

        domain = [
            ('journal_id', 'in', self.journal_ids.ids),
            ('date', '<=', self.date_from),
            ('reconciled', '=', False),  # Only unreconciled items
        ]

        # Filter by customer/supplier
        if self.result_selection == 'customer':
            domain.append(('account_id.account_type', '=', 'asset_receivable'))
        elif self.result_selection == 'supplier':
            domain.append(('account_id.account_type', '=', 'liability_payable'))
        else:
            # Both receivable and payable
            domain.append(('account_id.account_type', 'in', ['asset_receivable', 'liability_payable']))

        # Posted/all entries
        if self.target_move == 'posted':
            domain.append(('parent_state', '=', 'posted'))

        # Filter by specific partners if selected
        if self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))

        # Determine the action name based on report type
        if self.result_selection == 'customer':
            action_name = 'Aged Receivable Details'
        elif self.result_selection == 'supplier':
            action_name = 'Aged Payable Details'
        else:
            action_name = 'Aged Partner Balance Details'

        return {
            'name': action_name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'domain': domain,
            'view_mode': 'tree,form',
            'views': [(False, 'tree'), (False, 'form')],  # Explicitly define views
            'target': 'current',
            'context': {
                'search_default_group_by_partner': 1,
                'search_default_unreconciled': 1,
                'default_date': self.date_from,
            },
        }
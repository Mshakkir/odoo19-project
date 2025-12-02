from odoo import models, fields

class AccountAgedTrialBalance(models.TransientModel):
    _inherit = 'account.aged.trial.balance'

    def show_details(self):
        self.ensure_one()

        domain = [
            ('journal_id', 'in', self.journal_ids.ids),
            ('date', '<=', self.date_from),
        ]

        if self.result_selection == 'customer':
            domain.append(('account_id.account_type', '=', 'asset_receivable'))
        elif self.result_selection == 'supplier':
            domain.append(('account_id.account_type', '=', 'liability_payable'))

        if self.target_move == 'posted':
            domain.append(('parent_state', '=', 'posted'))

        if self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))

        # Lookup the views safely
        tree_view = self.env.ref('account.view_move_line_tree', raise_if_not_found=False)
        form_view = self.env.ref('account.view_move_line_form', raise_if_not_found=False)

        views = []
        if tree_view:
            views.append((tree_view.id, 'tree'))
        if form_view:
            views.append((form_view.id, 'form'))

        # Fallback to default if views not found
        if not views:
            views = [(False, 'tree'), (False, 'form')]

        return {
            'name': 'Aged Report Details',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'domain': domain,
            'view_mode': 'tree,form',
            'views': views,
            'target': 'current',
            'context': {'search_default_group_by_partner': 1},
        }

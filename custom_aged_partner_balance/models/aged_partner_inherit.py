from odoo import models

class AccountAgedTrialBalance(models.TransientModel):
    _inherit = 'account.aged.trial.balance'

    def show_details(self):
        """Open detailed move lines window (safe: supplies explicit views)."""
        self.ensure_one()

        domain = [
            ('journal_id', 'in', self.journal_ids.ids),
            ('date', '<=', self.date_from),
        ]

        if self.result_selection == 'customer':
            domain += [('account_id.account_type', '=', 'asset_receivable')]
        elif self.result_selection == 'supplier':
            domain += [('account_id.account_type', '=', 'liability_payable')]

        if self.target_move == 'posted':
            domain += [('parent_state', '=', 'posted')]

        if self.partner_ids:
            domain += [('partner_id', 'in', self.partner_ids.ids)]

        # Try to get standard account.move.line tree/form views if available
        tree_view = self.env.ref('account.view_move_line_tree', raise_if_not_found=False)
        form_view = self.env.ref('account.view_move_line_form', raise_if_not_found=False)

        views = []
        if tree_view:
            views.append((tree_view.id, 'tree'))
        if form_view:
            views.append((form_view.id, 'form'))

        # If standard views are not found, fallback to a generic list/form (Odoo will try to use defaults)
        if not views:
            views = [(False, 'tree'), (False, 'form')]

        return {
            'name': "Aged Report Details",
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'tree,form',
            'views': views,
            'domain': domain,
            'context': {'search_default_group_by_partner': 1},
            # optional: open in a new modal
            # 'target': 'new',
        }

from odoo import models

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

        # -------- GUARANTEED SAFE VIEW LOOKUP --------
        try:
            tree_view = self.env.ref('account.view_move_line_tree')
        except:
            tree_view = False

        try:
            form_view = self.env.ref('account.view_move_line_form')
        except:
            form_view = False

        views = []
        if tree_view:
            views.append((tree_view.id, 'tree'))
        if form_view:
            views.append((form_view.id, 'form'))

        # If NOTHING exists, fallback (avoids crash)
        if not views:
            views = [(False, 'tree'), (False, 'form')]

        return {
            'name': 'Aged Report Details',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'domain': domain,
            'view_mode': 'list,form',
            'views': views,
            'target': 'current',
            'context': {'search_default_group_by_partner': 1},
        }

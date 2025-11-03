from odoo import api, fields, models

class AccountDaybookAnalyticWizard(models.TransientModel):
    _inherit = 'account.daybook.report'

    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        'rel_daybook_analytic_account_rel',
        'wizard_id',
        'analytic_id',
        string='Analytic Accounts'
    )

    def action_show_details(self):
        """Show account move lines filtered by selected dates and analytic accounts"""
        self.ensure_one()
        domain = [('date', '>=', self.date_from), ('date', '<=', self.date_to)]

        if self.analytic_account_ids:
            domain.append(('analytic_account_id', 'in', self.analytic_account_ids.ids))

        # ✅ Try to find standard views safely
        tree_view = self.env.ref('account.view_move_line_tree', raise_if_not_found=False)
        form_view = self.env.ref('account.view_move_line_form', raise_if_not_found=False)

        # ✅ Prepare view list only for existing ones
        views = []
        if tree_view:
            views.append((tree_view.id, 'tree'))
        if form_view:
            views.append((form_view.id, 'form'))

        # ✅ Use view_mode dynamically based on what exists
        view_mode = 'tree,form' if views else 'list'

        return {
            'name': 'Analytic Account Details',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'views': views or False,   # safe fallback
            'view_mode': view_mode,
            'domain': domain,
            'target': 'current',
            'context': {'create': False},
        }

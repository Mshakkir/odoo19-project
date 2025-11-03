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

        # ✅ Use your verified view IDs
        tree_view = self.env.ref('account.view_move_line_tree', raise_if_not_found=False)
        form_view = self.env.ref('account.view_move_line_form', raise_if_not_found=False)

        views = []
        if tree_view:
            views.append((tree_view.id, 'tree'))
        if form_view:
            views.append((form_view.id, 'form'))

        if not views:
            raise ValueError("No valid tree or form view found for 'account.move.line'")

        return {
            'name': 'Analytic Account Details',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'views': views,
            'view_mode': 'list',
            'domain': domain,
            'target': 'current',
            'context': {'create': False},
        }

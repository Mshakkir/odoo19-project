from odoo import api, fields, models
from odoo.exceptions import UserError


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

        # Find available views for account.move.line
        tree_view = self.env['ir.ui.view'].search([
            ('model', '=', 'account.move.line'),
            ('type', '=', 'tree')
        ], limit=1)

        form_view = self.env['ir.ui.view'].search([
            ('model', '=', 'account.move.line'),
            ('type', '=', 'form')
        ], limit=1)

        if not tree_view:
            raise UserError("No tree view found for Journal Items. Please check your account module installation.")

        action = {
            'name': 'Analytic Account Details',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'domain': domain,
            'target': 'current',
            'context': {'create': False},
        }

        # Build views list
        views = [(tree_view.id, 'tree')]
        if form_view:
            views.append((form_view.id, 'form'))

        action['views'] = views
        action['view_mode'] = ','.join([v[1] for v in views])

        return action
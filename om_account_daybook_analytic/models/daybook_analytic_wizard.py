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

        # Try to get the standard Journal Items action
        try:
            action = self.env.ref('account.action_account_moves_all_a').sudo().read()[0]
            action['domain'] = domain
            action['context'] = dict(self.env.context, create=False, edit=False)
            action['name'] = 'Analytic Account Details'
            return action
        except:
            pass

        # Fallback: Try other common actions
        try:
            action = self.env.ref('account.action_move_line_select').sudo().read()[0]
            action['domain'] = domain
            action['context'] = dict(self.env.context, create=False, edit=False)
            action['name'] = 'Analytic Account Details'
            return action
        except:
            pass

        # Last resort: Search for ANY tree view
        IrView = self.env['ir.ui.view'].sudo()
        tree_view = IrView.search([
            ('model', '=', 'account.move.line'),
            ('type', '=', 'tree')
        ], limit=1, order='id asc')

        if not tree_view:
            # Try 'list' type instead of 'tree'
            tree_view = IrView.search([
                ('model', '=', 'account.move.line'),
                ('type', '=', 'list')
            ], limit=1, order='id asc')

        if not tree_view:
            raise UserError(
                "No list/tree view found for Journal Items (account.move.line). "
                "This might be a version compatibility issue. "
                "Please contact your system administrator."
            )

        return {
            'name': 'Analytic Account Details',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'tree,form',
            'views': [(tree_view.id, 'tree'), (False, 'form')],
            'domain': domain,
            'target': 'current',
            'context': {'create': False},
        }
from odoo import api, fields, models

class AccountDaybookAnalyticWizard(models.TransientModel):
    _inherit = 'account.daybook.report'

    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        'rel_daybook_analytic_account_rel',  # short table name
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

        return {
            'name': 'Analytic Account Details',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'tree,form',
            'domain': domain,
            'target': 'current',
            'context': {'create': False},
        }

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

        # Get all move lines in date range
        move_lines = self.env['account.move.line'].search([
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('display_type', '=', False)
        ])

        # Filter by analytic accounts if selected
        if self.analytic_account_ids:
            filtered_lines = move_lines.filtered(
                lambda line: line.analytic_distribution and
                             any(str(acc.id) in (line.analytic_distribution or {})
                                 for acc in self.analytic_account_ids)
            )
            domain = [('id', 'in', filtered_lines.ids)]
        else:
            domain = [('id', 'in', move_lines.ids)]

        return {
            'name': 'Analytic Account Details',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'list,form',
            'domain': domain,
            'target': 'current',
            'context': {'create': False},
        }
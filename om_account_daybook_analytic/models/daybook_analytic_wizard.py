from odoo import api, fields, models

class DaybookAnalyticWizard(models.TransientModel):
    _name = 'daybook.analytic.wizard'
    _description = 'Daybook Analytic Wizard'

    date_from = fields.Date(string='Start Date', required=True)
    date_to = fields.Date(string='End Date', required=True)
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')

    def action_show_details(self):
        self.ensure_one()
        domain = [('date', '>=', self.date_from), ('date', '<=', self.date_to)]
        if self.analytic_account_id:
            domain.append(('analytic_account_id', '=', self.analytic_account_id.id))

        # Here, we assume you want to show account.move.line (journal items)
        return {
            'name': 'Analytic Account Details',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'tree,form',
            'domain': domain,
            'target': 'current',
            'context': {'create': False},
        }

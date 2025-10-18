from odoo import api, fields, models


class BalanceSheetWizard(models.TransientModel):
    _name = "custom.balance.sheet.wizard"
    _description = "Balance Sheet Wizard"

    target_moves = fields.Selection([
        ('posted', 'All Posted Entries'),
        ('all', 'All Entries'),
    ], string="Target Moves", default='posted', required=True)

    date_from = fields.Date(string="Date From", required=True)
    date_to = fields.Date(string="Date To", required=True)

    def action_generate_report(self):
        """Open report result in new window"""
        return {
            'name': 'Balance Sheet Details',
            'type': 'ir.actions.act_window',
            'res_model': 'custom.balance.sheet.line',
            'view_mode': 'tree',
            'target': 'new',  # popup window
            'context': {
                'date_from': self.date_from,
                'date_to': self.date_to,
                'target_moves': self.target_moves,
            }
        }

from odoo import models, fields, api

class AccountSummaryWizard(models.TransientModel):
    _name = 'account.summary.wizard'
    _description = 'Account Summary Wizard'

    date_from = fields.Date('Date From')
    date_to = fields.Date('Date To')
    line_ids = fields.One2many('account.summary.line', 'wizard_id', string='Lines')

    @api.multi
    def action_show_summary(self):
        # Your summary line creation logic (aggregate by account)
        # Fill line_ids with summary lines
        pass

class AccountSummaryLine(models.TransientModel):
    _name = 'account.summary.line'
    _description = 'Account Summary Line'

    wizard_id = fields.Many2one('account.summary.wizard')
    account_id = fields.Many2one('account.account', string='Account')
    balance = fields.Float(string='Balance')

    def action_open_details(self):
        # This returns the move lines for that account, filtered by dates
        return {
            'type': 'ir.actions.act_window',
            'name': 'Account Details',
            'res_model': 'account.move.line',
            'view_mode': 'tree,form',
            'domain': [
                ('account_id', '=', self.account_id.id),
                # Optionally filter by date_from/date_to from the wizard
            ],
            'target': 'current',
        }

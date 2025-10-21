from odoo import models, fields, api

class CustomBalanceSheet(models.TransientModel):
    _name = "custom.balance.sheet"
    _description = "Custom Balance Sheet Wizard"

    target_moves = fields.Selection([
        ('posted', 'All Posted Entries'),
        ('all', 'All Entries'),
    ], string="Target Moves", default='posted', required=True)

    date_from = fields.Date(string="Date From", required=True)
    date_to = fields.Date(string="Date To", required=True)

    def action_generate_report(self):
        """Open Balance Sheet details in popup"""
        # Generate balance sheet lines before opening view
        self.env['custom.balance.sheet.line'].generate_lines(
            self.date_from, self.date_to, self.target_moves
        )

        return {
            'name': 'Balance Sheet Details',
            'type': 'ir.actions.act_window',
            'res_model': 'custom.balance.sheet.line',
            'view_mode': 'list,form',
            # 'target': 'new',  # open in popup
        }

    def action_print_pdf(self):
        """Generate PDF for balance sheet lines"""
        self.ensure_one()

        # Fetch all balance sheet lines (or only those within date range)
        lines = self.env['custom.balance.sheet.line'].search([])

        # Prepare data dictionary that will be available to QWeb as `data`
        data = {
            'form': {
                'date_from': self.date_from,
                'date_to': self.date_to,
                'target_moves': self.target_moves,
            },
            'line_ids': lines.ids,
        }

        # Return report action with data passed correctly
        return self.env.ref('custom_balance_sheet.action_custom_balance_sheet_pdf').report_action(self, data=data)

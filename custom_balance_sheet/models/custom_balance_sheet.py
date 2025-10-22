from odoo import models, fields, api
from odoo.exceptions import UserError


class CustomBalanceSheet(models.TransientModel):
    _name = "custom.balance.sheet"
    _description = "Custom Balance Sheet Wizard"

    # Selection field for target moves
    target_moves = fields.Selection([
        ('posted', 'All Posted Entries'),
        ('all', 'All Entries'),
    ], string="Target Moves", default='posted', required=True)

    # Date range fields
    date_from = fields.Date(string="Date From", required=True)
    date_to = fields.Date(string="Date To", required=True)

    # ----------------------------
    # Action to open report in a tree/form view
    # ----------------------------
    def action_generate_report(self):
        """Generate and open the balance sheet details in a view."""

        # Ensure date validity
        if self.date_from > self.date_to:
            raise UserError("The start date cannot be after the end date.")

        # Generate report lines
        lines = self.env['custom.balance.sheet.line'].generate_lines(
            self.date_from, self.date_to, self.target_moves
        )

        if not lines:
            raise UserError("No records found for the selected period.")

        # Open generated records in a list/form view
        return {
            'name': 'Balance Sheet Details',
            'type': 'ir.actions.act_window',
            'res_model': 'custom.balance.sheet.line',
            'view_mode': 'list,form',
            'domain': [('id', 'in', lines.ids)],
            # Uncomment next line if you want it in popup
            # 'target': 'new',
        }

    # ----------------------------
    # Action to print PDF report
    # ----------------------------
    def action_print_pdf(self):
        """Generate PDF for the balance sheet report."""
        self.ensure_one()

        if self.date_from > self.date_to:
            raise UserError("The start date cannot be after the end date.")

        # Fetch only lines generated for this date range
        lines = self.env['custom.balance.sheet.line'].search([
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ])

        if not lines:
            raise UserError("No records available to print for the selected period.")

        data = {
            'form': {
                'date_from': self.date_from,
                'date_to': self.date_to,
                'target_moves': self.target_moves,
            },
            'line_ids': lines.ids,
        }

        # Return report action (QWeb PDF)
        return self.env.ref('custom_balance_sheet.action_custom_balance_sheet_pdf').report_action(
            lines, data=data
        )







# from odoo import models, fields, api
#
# class CustomBalanceSheet(models.TransientModel):
#     _name = "custom.balance.sheet"
#     _description = "Custom Balance Sheet Wizard"
#
#     target_moves = fields.Selection([
#         ('posted', 'All Posted Entries'),
#         ('all', 'All Entries'),
#     ], string="Target Moves", default='posted', required=True)
#
#     date_from = fields.Date(string="Date From", required=True)
#     date_to = fields.Date(string="Date To", required=True)
#
#     def action_generate_report(self):
#         """Open Balance Sheet details in popup"""
#         # Generate balance sheet lines before opening view
#         self.env['custom.balance.sheet.line'].generate_lines(
#             self.date_from, self.date_to, self.target_moves
#         )
#
#         return {
#             'name': 'Balance Sheet Details',
#             'type': 'ir.actions.act_window',
#             'res_model': 'custom.balance.sheet.line',
#             'view_mode': 'list,form',
#             # 'target': 'new',  # open in popup
#         }
#
#     def action_print_pdf(self):
#         """Generate PDF for balance sheet lines"""
#         self.ensure_one()
#
#         # Fetch all balance sheet lines (or only those within date range)
#         lines = self.env['custom.balance.sheet.line'].search([])
#
#         # Prepare data dictionary that will be available to QWeb as `data`
#         data = {
#             'form': {
#                 'date_from': self.date_from,
#                 'date_to': self.date_to,
#                 'target_moves': self.target_moves,
#             },
#             'line_ids': lines.ids,
#         }
#
#         # Return report action with data passed correctly
#         return self.env.ref('custom_balance_sheet.action_custom_balance_sheet_pdf').report_action(
#             lines, data=data
#         )

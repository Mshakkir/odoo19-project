from odoo import models, fields, api, _
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
    # Generate and open balance sheet
    # ----------------------------
    def action_generate_report(self):
        """Generate and open the balance sheet details in a view."""

        # Validate dates
        if self.date_from > self.date_to:
            raise UserError(_("The start date cannot be after the end date."))

        # Generate report lines and return them
        lines = self.env['custom.balance.sheet.line'].generate_lines(
            self.date_from, self.date_to, self.target_moves
        )

        # If generate_lines() returns None, we fetch them manually
        if not lines:
            lines = self.env['custom.balance.sheet.line'].search([])

        return {
            'name': _('Balance Sheet Details'),
            'type': 'ir.actions.act_window',
            'res_model': 'custom.balance.sheet.line',
            'view_mode': 'list,form',
            'domain': [('id', 'in', lines.ids)],
            'target': 'current',
        }

    # ----------------------------
    # Print Balance Sheet PDF
    # ----------------------------
    def action_print_pdf(self):
        """Generate and print the Balance Sheet as PDF."""
        self.ensure_one()

        if self.date_from > self.date_to:
            raise UserError(_("The start date cannot be after the end date."))

        # ✅ FIX 1: Ensure lines are generated right before printing
        lines = self.env['custom.balance.sheet.line'].generate_lines(
            self.date_from, self.date_to, self.target_moves
        )

        # ✅ FIX 2: Get lines from the same transient model in memory
        lines = self.env['custom.balance.sheet.line'].search([])

        if not lines:
            raise UserError(_("No records available to print for the selected period."))

        data = {
            'form': {
                'date_from': self.date_from,
                'date_to': self.date_to,
                'target_moves': self.target_moves,
            },
            'line_ids': lines.ids,
        }

        # ✅ FIX 3: Pass `lines` (not empty wizard) to report
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

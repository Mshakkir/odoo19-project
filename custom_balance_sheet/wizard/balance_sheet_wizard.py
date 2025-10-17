from odoo import models, fields, api
from odoo.exceptions import UserError

class BalanceSheetWizard(models.TransientModel):
    _name = "balance.sheet.wizard"
    _description = "Balance Sheet Wizard"

    date_from = fields.Date(string="Start Date", required=True)
    date_to = fields.Date(string="End Date", required=True)

    def print_balance_sheet(self):
        data = {
            'date_from': self.date_from,
            'date_to': self.date_to,
        }
        return self.env.ref('custom_balance_sheet.action_balance_sheet_report').report_action(self, data=data)

from odoo import models, fields

class BalanceSheetWizard(models.TransientModel):
    _name = "balance.sheet.wizard"
    _description = "Balance Sheet Wizard"

    date_from = fields.Date(string="Start Date", required=True)
    date_to = fields.Date(string="End Date", required=True)

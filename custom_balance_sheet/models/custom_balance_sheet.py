# models/custom_balance_sheet.py
from odoo import models, fields

class CustomBalanceSheet(models.TransientModel):
    _name = "custom.balance.sheet"
    _description = "Custom Balance Sheet Wizard"

    # Example field
    date = fields.Date(string="As of Date")

from odoo import fields, models

class BankStatementLine(models.TransientModel):
    _name = "bank.statement.line"
    _description = "Bank Statement Wizard Lines"

    wizard_id = fields.Many2one("bank.statement", string="Wizard", ondelete="cascade")
    move_line_id = fields.Many2one("account.move.line", string="Journal Item")
    statement_date = fields.Date(string="Statement Date")

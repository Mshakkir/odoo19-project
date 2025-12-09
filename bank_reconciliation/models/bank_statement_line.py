from odoo import fields, models


class BankStatementLine(models.Model):
    _name = "bank.statement.line"
    _description = "Bank Statement Record Lines"

    wizard_id = fields.Many2one("bank.statement", string="Wizard", ondelete="cascade")
    move_line_id = fields.Many2one("account.move.line", string="Move Line")
    statement_date = fields.Date(string="Statement Date")

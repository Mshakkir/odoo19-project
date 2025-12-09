# -*- coding: utf-8 -*-
from odoo import fields, models


class BankStatementLine(models.TransientModel):
    _name = "bank.statement.line"
    _description = "Bank Statement Wizard Lines"

    wizard_id = fields.Many2one("bank.statement", string="Wizard", ondelete="cascade")
    move_line_id = fields.Many2one("account.move.line", string="Journal Item", required=True)
    statement_date = fields.Date(string="Statement Date")

    # Related fields from move_line_id for display
    date = fields.Date(related='move_line_id.date', string='Date', readonly=True)
    move_id = fields.Many2one(related='move_line_id.move_id', string='Journal Entry', readonly=True)
    name = fields.Char(related='move_line_id.name', string='Label', readonly=True)
    ref = fields.Char(related='move_line_id.ref', string='Reference', readonly=True)
    partner_id = fields.Many2one(related='move_line_id.partner_id', string='Partner', readonly=True)
    debit = fields.Monetary(related='move_line_id.debit', string='Debit', readonly=True)
    credit = fields.Monetary(related='move_line_id.credit', string='Credit', readonly=True)
    amount_currency = fields.Monetary(related='move_line_id.amount_currency', string='Amount Currency', readonly=True)
    currency_id = fields.Many2one(related='move_line_id.currency_id', string='Currency', readonly=True)
    date_maturity = fields.Date(related='move_line_id.date_maturity', string='Due Date', readonly=True)
    company_currency_id = fields.Many2one(related='move_line_id.company_currency_id', readonly=True)
    company_id = fields.Many2one(related='move_line_id.company_id', readonly=True)
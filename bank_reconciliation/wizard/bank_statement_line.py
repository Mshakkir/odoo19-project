# -*- coding: utf-8 -*-
from odoo import fields, models, api


class BankStatementLine(models.TransientModel):
    _name = "bank.statement.line"
    _description = "Bank Statement Wizard Lines"

    wizard_id = fields.Many2one("bank.statement", string="Wizard", ondelete="cascade", required=True)
    move_line_id = fields.Many2one("account.move.line", string="Journal Item", required=True)
    statement_date = fields.Date(string="Statement Date")

    # Related fields from move_line_id for display
    date = fields.Date(related='move_line_id.date', string='Date', readonly=True, store=False)
    move_id = fields.Many2one(related='move_line_id.move_id', string='Journal Entry', readonly=True, store=False)
    name = fields.Char(related='move_line_id.name', string='Label', readonly=True, store=False)
    ref = fields.Char(related='move_line_id.ref', string='Reference', readonly=True, store=False)
    partner_id = fields.Many2one(related='move_line_id.partner_id', string='Partner', readonly=True, store=False)
    debit = fields.Monetary(related='move_line_id.debit', string='Debit', readonly=True, store=False,
                            currency_field='company_currency_id')
    credit = fields.Monetary(related='move_line_id.credit', string='Credit', readonly=True, store=False,
                             currency_field='company_currency_id')
    amount_currency = fields.Monetary(related='move_line_id.amount_currency', string='Amount Currency', readonly=True,
                                      store=False)
    currency_id = fields.Many2one(related='move_line_id.currency_id', string='Currency', readonly=True, store=False)
    date_maturity = fields.Date(related='move_line_id.date_maturity', string='Due Date', readonly=True, store=False)
    company_currency_id = fields.Many2one(related='move_line_id.company_currency_id', readonly=True, store=False)
    company_id = fields.Many2one(related='move_line_id.company_id', readonly=True, store=False)
# -*- coding: utf-8 -*-
from odoo import models, fields, api


class PurchaseBookPreview(models.TransientModel):
    _name = 'purchase.book.preview'
    _description = 'Purchase Book Preview Line'
    _order = 'date asc, sequence asc'

    wizard_id = fields.Many2one('purchase.book.wizard', string='Wizard', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)

    # Common fields
    date = fields.Date(string='Date', required=True)
    transaction_type = fields.Char(string='Type')
    vendor = fields.Char(string='Vendor')
    invoice_ref = fields.Char(string='Invoice/Ref')

    # Amount fields
    gross = fields.Float(string='Gross', digits=(16, 2))
    trade_disc = fields.Float(string='Tr. Disc', digits=(16, 2))
    net_total = fields.Float(string='Net Total', digits=(16, 2))
    add_disc = fields.Float(string='Ad. Disc', digits=(16, 2))
    add_cost = fields.Float(string='Ad. Cost', digits=(16, 2))
    round_off = fields.Float(string='Round Off', digits=(16, 2))
    adj_amount = fields.Float(string='Adj. Amt', digits=(16, 2))
    tax_amount = fields.Float(string='Tax Amt', digits=(16, 2))
    grand_total = fields.Float(string='Grand Total', digits=(16, 2))

    # For subtotal rows
    is_subtotal = fields.Boolean(string='Is Subtotal', default=False)
    subtotal_label = fields.Char(string='Subtotal Label')
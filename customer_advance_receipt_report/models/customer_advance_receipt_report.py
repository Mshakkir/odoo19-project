# -*- coding: utf-8 -*-

from odoo import models, fields, api


class CustomerAdvanceReceiptReport(models.TransientModel):
    _name = 'customer.advance.receipt.report'
    _description = 'Customer Advance Receipt Report'
    _order = 'date desc, receipt_number desc'

    date = fields.Date(string='Date', required=True)
    receipt_number = fields.Char(string='Receipt Number', required=True)
    journal_name = fields.Char(string='Journal', required=True)
    payment_method = fields.Char(string='Payment Method', required=True)
    customer_name = fields.Char(string='Customer Name', required=True)
    amount = fields.Float(string='Amount', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency')

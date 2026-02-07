# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SalespersonReportDisplay(models.TransientModel):
    _name = 'salesperson.report.display'
    _description = 'Salesperson Report Display'
    _rec_name = 'salesperson_name'

    salesperson_id = fields.Many2one('res.users', string='Salesperson', readonly=True)
    salesperson_name = fields.Char(string='Sales Person', readonly=True)
    invoice_date = fields.Date(string='Date', readonly=True)
    invoice_number = fields.Char(string='Inv No', readonly=True)
    customer_name = fields.Char(string='Customer Name', readonly=True)
    account_code = fields.Char(string='Sales Ac', readonly=True)
    product_code = fields.Char(string='Code', readonly=True)
    product_name = fields.Char(string='Name', readonly=True)
    quantity = fields.Float(string='Qty', readonly=True)
    uom = fields.Char(string='Unit', readonly=True)
    price_unit = fields.Float(string='Rate', readonly=True)
    discount = fields.Float(string='Discount', readonly=True)
    price_subtotal = fields.Float(string='Net Total', readonly=True)
    invoice_id = fields.Integer(string='Invoice ID', readonly=True)
    is_invoice_line = fields.Boolean(string='Is Invoice Line', default=True, readonly=True)
    sequence = fields.Integer(string='Sequence', readonly=True)


class SalespersonReportSummary(models.TransientModel):
    _name = 'salesperson.report.summary'
    _description = 'Salesperson Report Summary'

    name = fields.Char(string='Summary', readonly=True)
    total_amount = fields.Float(string='Total Amount', readonly=True)
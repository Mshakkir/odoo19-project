from odoo import models, fields, api


class SalesRegisterDetails(models.TransientModel):
    _name = 'sales.register.details'
    _description = 'Sales Register Details View'

    wizard_id = fields.Many2one('sales.register.wizard', string='Wizard Reference')
    date = fields.Date(string='Date')
    document_type = fields.Char(string='Type')
    document_number = fields.Char(string='Document No.')
    customer_name = fields.Char(string='Customer')
    customer_vat = fields.Char(string='VAT')
    warehouse = fields.Char(string='Warehouse')
    product = fields.Char(string='Product')
    quantity = fields.Float(string='Qty', digits='Product Unit of Measure')
    unit_price = fields.Float(string='Unit Price', digits='Product Price')
    subtotal = fields.Float(string='Subtotal', digits='Product Price')
    trade_discount = fields.Float(string='Trade Discount', digits='Product Price')
    addin_discount = fields.Float(string='Additional Discount', digits='Product Price')
    addin_cost = fields.Float(string='Additional Cost', digits='Product Price')
    taxes = fields.Char(string='Tax')
    tax_amount = fields.Float(string='Tax Amount', digits='Product Price')
    round_off = fields.Float(string='Round Off', digits='Product Price')
    total = fields.Float(string='Total', digits='Product Price')
    paid = fields.Float(string='Received', digits='Product Price')
    balance = fields.Float(string='Balance', digits='Product Price')
    currency = fields.Char(string='Currency')
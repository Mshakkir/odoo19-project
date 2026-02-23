from odoo import models, fields


class SalesEstimationStatusDetails(models.TransientModel):
    _name = 'sales.estimation.status.details'
    _description = 'Sales Estimation Status Details'

    wizard_id = fields.Many2one('sales.estimation.status.wizard', string='Wizard Reference')
    date = fields.Date(string='Date')
    estimation_type = fields.Char(string='Type')
    form_type = fields.Char(string='Form Type')
    bill_mode = fields.Char(string='Bill Mode')
    document_number = fields.Char(string='Document No.')
    customer_name = fields.Char(string='Party')
    customer_vat = fields.Char(string='VAT/TRN')
    product = fields.Char(string='Product')
    quantity = fields.Float(string='Qty', digits='Product Unit of Measure')
    unit_price = fields.Float(string='Unit Price', digits='Product Price')
    subtotal = fields.Float(string='Subtotal', digits='Product Price')
    discount = fields.Float(string='Discount', digits='Product Price')
    taxes = fields.Char(string='Tax')
    tax_amount = fields.Float(string='Tax Amount', digits='Product Price')
    total = fields.Float(string='Total', digits='Product Price')
    state = fields.Char(string='Status')
    currency = fields.Char(string='Currency')
    use_ledger_currency = fields.Boolean(string='Ledger Currency')
from odoo import models, fields


class SalesEstimationStatusDetails(models.TransientModel):
    _name = 'sales.estimation.status.details'
    _description = 'Sales Estimation Status Details'

    wizard_id = fields.Many2one('sales.estimation.status.wizard', string='Wizard Reference')

    # ── New first columns ──────────────────────────────────────────────────────
    date = fields.Date(string='Date')
    vno = fields.Char(string='Vno')
    warehouse = fields.Char(string='Warehouse')
    customer_name = fields.Char(string='Customer Name')
    address = fields.Char(string='Address')
    cell_no = fields.Char(string='Cell No')
    sales_account = fields.Char(string='Sales Account')

    # ── Existing columns ───────────────────────────────────────────────────────
    estimation_type = fields.Char(string='Type')
    form_type = fields.Char(string='Form Type')
    bill_mode = fields.Char(string='Bill Mode')
    document_number = fields.Char(string='Document No.')
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
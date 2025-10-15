from odoo import models, fields, api

class ProductStockLedgerWizard(models.TransientModel):
    _name = 'product.stock.ledger.wizard'
    _description = 'Product Stock Ledger Wizard'

    product_id = fields.Many2one('product.product', string="Product", required=True)
    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse")
    date_from = fields.Date(string="Date From", required=True)
    date_to = fields.Date(string="Date To", required=True)

    # These are the missing fields used in the view
    date = fields.Datetime(string="Date")
    voucher = fields.Char(string="Voucher")
    particulars = fields.Char(string="Particulars")
    move_type = fields.Char(string="Type")

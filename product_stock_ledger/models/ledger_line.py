# product_stock_ledger/controllers/ledger_line.py
from odoo import models, fields, api

class ProductStockLedgerLine(models.TransientModel):
    _name = 'product.stock.ledger.line'
    _description = 'Temporary lines for product stock ledger'

    wizard_id = fields.Many2one('product.stock.ledger.wizard', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    date = fields.Datetime(string='Date')
    voucher = fields.Char(string='Voucher')
    particulars = fields.Char(string='Particulars')
    type = fields.Char(string='Type')
    rec_qty = fields.Float(string='Rec. Qty')
    rec_rate = fields.Float(string='Rec. Rate')
    issue_qty = fields.Float(string='Issue Qty')
    issue_rate = fields.Float(string='Issue Rate')
    balance = fields.Float(string='Balance')
    uom = fields.Char(string='Unit')
    invoice_status = fields.Char(string='Invoice Status')

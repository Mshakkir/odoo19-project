from odoo import models, fields, api


class PurchaseWarehouseReport(models.TransientModel):
    _name = 'purchase.warehouse.report'
    _description = 'Purchase Warehouse Report'
    _order = 'invoice_date desc, invoice_number'

    invoice_date = fields.Date(string='Date', readonly=True)
    invoice_number = fields.Char(string='Invoice Number', readonly=True)
    vendor_id = fields.Many2one('res.partner', string='Vendor Name', readonly=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', readonly=True)
    product_id = fields.Many2one('product.product', string='Product Name', readonly=True)
    quantity = fields.Float(string='Qty', readonly=True)
    uom_id = fields.Many2one('uom.uom', string='Unit', readonly=True)
    price_unit = fields.Float(string='Rate', readonly=True)
    net_amount = fields.Float(string='Net Amount', readonly=True)
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', readonly=True)

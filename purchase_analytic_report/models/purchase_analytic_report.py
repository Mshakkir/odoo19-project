from odoo import models, fields, api


class PurchaseAnalyticReport(models.TransientModel):
    _name = 'purchase.analytic.report'
    _description = 'Purchase Analytic Report'
    _order = 'invoice_date desc, invoice_number, id'

    invoice_date = fields.Date(string='Date', readonly=True)
    invoice_number = fields.Char(string='Invoice Number', readonly=True)
    vendor_id = fields.Many2one('res.partner', string='Vendor Name', readonly=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', readonly=True)
    product_id = fields.Many2one('product.product', string='Product Name', readonly=True)
    quantity = fields.Float(string='Qty', readonly=True, digits='Product Unit of Measure')
    uom_id = fields.Many2one('uom.uom', string='Unit', readonly=True)
    unit_price = fields.Float(string='Rate', readonly=True, digits='Product Price')
    net_amount = fields.Float(string='Net Amount', readonly=True, digits='Account')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', readonly=True)
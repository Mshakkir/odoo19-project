from odoo import models, fields, api


class PurchaseProductReportNew(models.TransientModel):
    _name = 'purchase.bypd.report'
    _description = 'Purchase Product Report'
    _order = 'invoice_date desc, invoice_number'

    invoice_date = fields.Date(string='Date', readonly=True)
    invoice_number = fields.Char(string='Invoice Number', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    quantity = fields.Float(string='Quantity', readonly=True)
    uom_id = fields.Many2one('uom.uom', string='Unit', readonly=True)
    price_unit = fields.Float(string='Rate', readonly=True)
    price_total = fields.Float(string='Net Total', readonly=True)
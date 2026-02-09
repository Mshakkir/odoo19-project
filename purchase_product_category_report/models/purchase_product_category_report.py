from odoo import models, fields, api


class PurchaseProductCategoryReport(models.TransientModel):
    _name = 'purchase.product.category.report'
    _description = 'Purchase Product Category Report'
    _order = 'invoice_date desc, invoice_number'

    invoice_date = fields.Date(string='Date', readonly=True)
    invoice_number = fields.Char(string='Invoice Number', readonly=True)
    vendor_id = fields.Many2one('res.partner', string='Vendor Name', readonly=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', readonly=True)
    buyer_id = fields.Many2one('res.users', string='Buyer', readonly=True)
    product_category_id = fields.Many2one('product.category', string='Product Category', readonly=True)
    product_id = fields.Many2one('product.product', string='Product Name', readonly=True)
    quantity = fields.Float(string='Qty', readonly=True)
    uom_id = fields.Many2one('uom.uom', string='Unit', readonly=True)
    price_unit = fields.Float(string='Rate', readonly=True)
    discount = fields.Float(string='Discount (Fixed)', readonly=True)
    untaxed_amount = fields.Float(string='Untaxed Amount', readonly=True)
    tax_value = fields.Float(string='Tax Value', readonly=True)
    net_amount = fields.Float(string='Net Amount', readonly=True)
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', readonly=True)

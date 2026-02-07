from odoo import models, fields, api


class PurchaseVendorReport(models.TransientModel):
    _name = 'purchase.vendor.report'
    _description = 'Purchase Vendor Report'
    _order = 'invoice_date desc, invoice_number'

    invoice_date = fields.Date(string='Date', readonly=True)
    invoice_number = fields.Char(string='Invoice Number', readonly=True)
    vendor_id = fields.Many2one('res.partner', string='Vendor Name', readonly=True)
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', readonly=True)
    purchase_account_id = fields.Many2one('account.account', string='Purchase Account', readonly=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', readonly=True)
    net_amount = fields.Float(string='Net Amount', readonly=True)
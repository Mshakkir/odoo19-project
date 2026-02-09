# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductProfitMarginReport(models.TransientModel):
    _name = 'product.profit.margin.report'
    _description = 'Product Profit Margin Report'
    _order = 'date desc, product_name'

    date = fields.Date(string='Date', readonly=True)
    order_ref = fields.Char(string='Order Reference', readonly=True)
    product_id = fields.Integer(string='Product ID', readonly=True)
    product_name = fields.Char(string='Product', readonly=True)
    product_code = fields.Char(string='Product Code', readonly=True)
    category = fields.Char(string='Category', readonly=True)
    qty = fields.Float(string='Qty', readonly=True, digits=(16, 2))
    uom = fields.Char(string='Unit', readonly=True)
    rate = fields.Float(string='Rate', readonly=True, digits=(16, 2))
    total = fields.Float(string='Total', readonly=True, digits=(16, 2))
    unit_cost = fields.Float(string='Unit Cost', readonly=True, digits=(16, 2))
    total_cost = fields.Float(string='Total Cost', readonly=True, digits=(16, 2))
    profit = fields.Float(string='Profit', readonly=True, digits=(16, 2))
    profit_margin = fields.Float(string='Profit Margin %', compute='_compute_profit_margin', readonly=True, digits=(16, 2))

    @api.depends('total', 'total_cost')
    def _compute_profit_margin(self):
        """Calculate profit margin percentage"""
        for record in self:
            if record.total > 0:
                record.profit_margin = ((record.total - record.total_cost) / record.total) * 100
            else:
                record.profit_margin = 0.0
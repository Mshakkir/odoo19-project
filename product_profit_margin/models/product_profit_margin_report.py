# -*- coding: utf-8 -*-

from odoo import models, fields


class ProductProfitMarginReport(models.Model):
    _name = 'product.profit.margin.report'
    _description = 'Product Profit Margin Report'
    _order = 'date desc, product_name'
    _rec_name = 'product_name'

    date = fields.Date(string='Date', readonly=True, index=True)
    order_ref = fields.Char(string='Order Reference', readonly=True, index=True)
    product_id = fields.Integer(string='Product ID', readonly=True, index=True)
    product_name = fields.Char(string='Product', readonly=True, index=True)
    product_code = fields.Char(string='Product Code', readonly=True)
    category = fields.Char(string='Category', readonly=True, index=True)
    qty = fields.Float(string='Qty', readonly=True, digits=(16, 2))
    uom = fields.Char(string='Unit', readonly=True)
    rate = fields.Float(string='Rate', readonly=True, digits=(16, 2))
    total = fields.Float(string='Total', readonly=True, digits=(16, 2))
    unit_cost = fields.Float(string='Unit Cost', readonly=True, digits=(16, 2))
    total_cost = fields.Float(string='Total Cost', readonly=True, digits=(16, 2))
    profit = fields.Float(string='Profit', readonly=True, digits=(16, 2))
    profit_margin = fields.Float(string='Profit Margin %', readonly=True, digits=(16, 2))
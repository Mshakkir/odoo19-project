# -*- coding: utf-8 -*-
from odoo import models, fields


class PurchaseSalesComparisonLine(models.TransientModel):
    _name = 'purchase.sales.comparison.line'
    _description = 'Purchase Sales Comparison Line'

    wizard_id = fields.Many2one('purchase.sales.comparison.wizard', string='Wizard')
    code = fields.Char(string='Code')
    product_name = fields.Char(string='Product')
    uom = fields.Char(string='Unit')
    pur_qty = fields.Float(string='Pur.Qty', digits=(16, 2))
    pur_total = fields.Float(string='Pur.Total', digits=(16, 2))
    sal_qty = fields.Float(string='Sal.Qty', digits=(16, 2))
    sal_total = fields.Float(string='Sal.Total', digits=(16, 2))
    balance_qty = fields.Float(string='Balance Qty', digits=(16, 2))
    diff_amount = fields.Float(string='Diff.Amount', digits=(16, 2))

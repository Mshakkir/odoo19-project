from odoo import models, fields, api
from datetime import date

class ReorderActivity(models.Model):
    _name = "reorder.activity"
    _description = "Reorder Activity Logger"

    warehouse_id = fields.Many2one('stock.warehouse')
    product_id = fields.Many2one('product.product')
    qty_available = fields.Float()
    min_qty = fields.Float()

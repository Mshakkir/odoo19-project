from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string="Default Warehouse",
        help="Select the warehouse this product belongs to."
    )

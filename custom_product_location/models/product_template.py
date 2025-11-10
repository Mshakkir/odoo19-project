from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    default_location_id = fields.Many2one(
        'stock.location',
        string='Default Rack/Location',
        domain="[('usage', '=', 'internal')]",
        help='Default storage location for this product'
    )
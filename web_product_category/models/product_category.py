from odoo import models, fields


class ProductCategory(models.Model):
    _inherit = 'product.category'

    description = fields.Html(
        string='Description',
        help='Detailed description of the product category'
    )

    image_1920 = fields.Image(
        string='Image',
        max_width=1920,
        max_height=1920,
        help='Category image for website display'
    )

    image_512 = fields.Image(
        string='Image 512',
        related='image_1920',
        max_width=512,
        max_height=512,
        store=True
    )

    image_256 = fields.Image(
        string='Image 256',
        related='image_1920',
        max_width=256,
        max_height=256,
        store=True
    )
from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale


class CustomProductController(WebsiteSale):

    @http.route(['/shop/product/<model("product.template"):product>'], type='http', auth="public", website=True,
                sitemap=True)
    def product(self, product, category='', search='', **kwargs):
        """Override product detail page to add related products"""
        result = super(CustomProductController, self).product(
            product=product,
            category=category,
            search=search,
            **kwargs
        )

        # Add related products to the context
        if hasattr(result, 'qcontext'):
            related_products = request.env['product.template'].sudo().search([
                ('is_published', '=', True),
                ('id', '!=', product.id),
                ('categ_id', '=', product.categ_id.id),
            ], limit=4)
            result.qcontext['related_products'] = related_products

        return result
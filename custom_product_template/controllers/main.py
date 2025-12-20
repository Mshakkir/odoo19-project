from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale


class CustomProductController(WebsiteSale):

    @http.route(['/shop', '/shop/page/<int:page>'], type='http', auth="public", website=True)
    def shop(self, page=0, category=None, search='', min_price=0.0, max_price=0.0, ppg=False, **post):
        """Override shop route to add custom logic if needed"""
        result = super(CustomProductController, self).shop(
            page=page,
            category=category,
            search=search,
            min_price=min_price,
            max_price=max_price,
            ppg=ppg,
            **post
        )

        # Add custom values to the result
        if hasattr(result, 'qcontext'):
            # Get product categories
            categories = request.env['product.public.category'].search([])
            result.qcontext['product_categories'] = categories

            # Get featured products (optional)
            featured_products = request.env['product.template'].sudo().search([
                ('website_published', '=', True),
                ('is_published', '=', True),
            ], limit=8, order='create_date desc')
            result.qcontext['featured_products'] = featured_products

        return result

    @http.route(['/shop/product/<model("product.template"):product>'], type='http', auth="public", website=True)
    def product(self, product, category='', search='', **kwargs):
        """Override product detail page"""
        result = super(CustomProductController, self).product(
            product=product,
            category=category,
            search=search,
            **kwargs
        )

        # Add related products
        if hasattr(result, 'qcontext'):
            related_products = request.env['product.template'].sudo().search([
                ('website_published', '=', True),
                ('is_published', '=', True),
                ('id', '!=', product.id),
                ('categ_id', '=', product.categ_id.id),
            ], limit=4)
            result.qcontext['related_products'] = related_products

        return result
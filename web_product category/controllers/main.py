from odoo import http
from odoo.http import request


class ProductCategoryController(http.Controller):

    @http.route('/categories', type='http', auth='public', website=True)
    def product_categories(self, **kwargs):
        """
        Display product categories dynamically
        """
        # Fetch all product categories (you can add domain filters as needed)
        categories = request.env['product.category'].sudo().search([
            ('parent_id', '=', False)  # Get only parent categories
            # Add more filters if needed, e.g., ('active', '=', True)
        ], order='name asc')

        # You can also get all categories including children:
        # categories = request.env['product.category'].sudo().search([], order='name asc')

        return request.render('your_module_name.dynamic_product_categories', {
            'categories': categories,
        })


class ProductCategoryAPI(http.Controller):

    @http.route('/api/categories', type='json', auth='public', methods=['POST'])
    def get_categories_json(self, **kwargs):
        """
        API endpoint to get categories as JSON (optional, for AJAX requests)
        """
        categories = request.env['product.category'].sudo().search([
            ('parent_id', '=', False)
        ])

        result = []
        for category in categories:
            result.append({
                'id': category.id,
                'name': category.name,
                'description': category.description if hasattr(category, 'description') else '',
                'product_count': category.product_count,
                'image': category.image_1920.decode('utf-8') if category.image_1920 else False,
            })

        return result
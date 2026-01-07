from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale


class DynamicCategoryController(http.Controller):

    @http.route(['/shop/categories'], type='http', auth="public", website=True, sitemap=False)
    def category_page(self, **kwargs):
        """Render the dynamic category page with product categories"""

        # Fetch published product categories
        categories = request.env['product.public.category'].search([
            ('website_published', '=', True)
        ], order='sequence, name', limit=10)

        # Prepare category data
        category_data = []
        for category in categories:
            # Get sample product from this category
            product = request.env['product.template'].search([
                ('public_categ_ids', 'in', category.id),
                ('website_published', '=', True)
            ], limit=1)

            category_info = {
                'id': category.id,
                'name': category.name,
                'description': category.description or f"{category.name} products for industrial automation and control systems.",
                'image_url': f'/web/image/product.public.category/{category.id}/image_512' if category.image_128 else '/web/static/img/placeholder.png',
                'product_count': len(category.product_tmpl_ids),
                'slug': category.name.lower().replace(' ', '-').replace('/', '-'),
                'features': self._get_category_features(category),
                'url': f'/shop/category/{category.id}'
            }
            category_data.append(category_info)

        values = {
            'categories': category_data,
            'page_name': 'category',
        }

        return request.render('dynamic_category.category_page_template', values)

    def _get_category_features(self, category):
        """Extract or generate features for the category"""
        if category.description:
            # Try to extract bullet points from description
            lines = category.description.split('\n')
            features = [line.strip('- •*').strip() for line in lines if line.strip() and len(line.strip()) > 3]
            if features:
                return features[:3]  # Return top 3 features

        # Default features based on category
        default_features = {
            'push button': ['Emergency stop buttons', 'Start/Stop control', 'Panel mounted'],
            'solenoid': ['Fast switching', 'High reliability', 'Used in automation lines'],
            'pressure': ['High accuracy', 'Digital and analog output', 'Industrial grade'],
            'regulator': ['Stable output', 'Protects components', 'Energy efficient'],
            'silencer': ['Noise reduction', 'Easy installation', 'Durable materials'],
        }

        name_lower = category.name.lower()
        for key, features in default_features.items():
            if key in name_lower:
                return features

        # Generic features
        return ['High quality', 'Reliable performance', 'Industrial grade']
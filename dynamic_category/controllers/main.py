# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.http_routing.models.ir_http import slug


class DynamicCategoryController(http.Controller):

    @http.route(['/categories'], type='http', auth="public", website=True, sitemap=True)
    def category_showcase_page(self, **kwargs):
        """Render the category showcase page - displays all categories with details"""

        # Fetch all published product categories (parent and child)
        all_categories = request.env['product.public.category'].sudo().search([
            ('website_published', '=', True)
        ], order='sequence, name')

        # Organize categories by parent
        parent_categories = []

        for category in all_categories:
            if not category.parent_id:
                # This is a parent category
                children = all_categories.filtered(lambda c: c.parent_id.id == category.id)

                category_info = {
                    'id': category.id,
                    'name': category.name,
                    'description': category.description or self._get_default_description(category.name),
                    'image_url': self._get_category_image(category),
                    'product_count': len(category.product_tmpl_ids.filtered(lambda p: p.website_published)),
                    'url': f'/shop/category/{slug(category)}',
                    'slug': slug(category),
                    'children': []
                }

                # Add children
                for child in children:
                    child_info = {
                        'id': child.id,
                        'name': child.name,
                        'description': child.description or self._get_default_description(child.name),
                        'image_url': self._get_category_image(child),
                        'product_count': len(child.product_tmpl_ids.filtered(lambda p: p.website_published)),
                        'url': f'/shop/category/{slug(child)}',
                        'slug': slug(child),
                    }
                    category_info['children'].append(child_info)

                parent_categories.append(category_info)

        # Also get categories without parents that weren't included
        orphan_categories = all_categories.filtered(
            lambda c: not c.parent_id and c.id not in [p['id'] for p in parent_categories])
        for category in orphan_categories:
            category_info = {
                'id': category.id,
                'name': category.name,
                'description': category.description or self._get_default_description(category.name),
                'image_url': self._get_category_image(category),
                'product_count': len(category.product_tmpl_ids.filtered(lambda p: p.website_published)),
                'url': f'/shop/category/{slug(category)}',
                'slug': slug(category),
                'children': []
            }
            parent_categories.append(category_info)

        values = {
            'categories': parent_categories,
            'page_name': 'categories_showcase',
            'total_categories': len(all_categories),
        }

        return request.render('dynamic_category.category_showcase_template', values)

    @http.route(['/category/<model("product.public.category"):category>'],
                type='http', auth="public", website=True, sitemap=True)
    def category_detail(self, category, **kwargs):
        """Render detailed category page with child categories"""

        if not category.exists() or not category.website_published:
            return request.not_found()

        # Get child categories
        child_categories = request.env['product.public.category'].sudo().search([
            ('parent_id', '=', category.id),
            ('website_published', '=', True)
        ], order='sequence, name')

        # Prepare main category data
        main_category = {
            'id': category.id,
            'name': category.name,
            'description': category.description or self._get_default_description(category.name),
            'image_url': self._get_category_image(category),
            'slug': slug(category),
            'shop_url': f'/shop/category/{slug(category)}',  # Direct shop link
            'breadcrumbs': self._get_breadcrumbs(category),
        }

        # Prepare child categories data
        child_categories_data = []
        for child in child_categories:
            child_info = {
                'id': child.id,
                'name': child.name,
                'description': child.description or self._get_default_description(child.name),
                'image_url': self._get_category_image(child),
                'slug': slug(child),
                'product_count': len(child.product_tmpl_ids.filtered(lambda p: p.website_published)),
                'url': f'/category/{slug(child)}',  # Category detail page
                'shop_url': f'/shop/category/{slug(child)}',  # Direct shop link
            }
            child_categories_data.append(child_info)

        values = {
            'main_category': main_category,
            'child_categories': child_categories_data,
            'category_id': category.id,
            'page_name': 'category_detail',
        }

        return request.render('dynamic_category.category_detail_template', values)

    def _get_category_image(self, category):
        """Get category image URL"""
        if category.image_128:
            return f'/web/image/product.public.category/{category.id}/image_1024'

        # Fallback: Try to get image from a product in this category
        product = request.env['product.template'].sudo().search([
            ('public_categ_ids', 'in', category.id),
            ('website_published', '=', True),
            ('image_1920', '!=', False)
        ], limit=1)

        if product:
            return f'/web/image/product.template/{product.id}/image_512'

        return '/web/static/img/placeholder.png'

    def _get_default_description(self, category_name):
        """Generate default description based on category name"""
        descriptions = {
            'pneumatic': 'High-quality pneumatic components for industrial automation, including valves, cylinders, and air preparation equipment.',
            'valve': 'Precision control valves for fluid and air management in industrial applications.',
            'sensor': 'Advanced sensing solutions for monitoring pressure, temperature, and position in automation systems.',
            'cylinder': 'Reliable pneumatic and hydraulic cylinders for linear motion control.',
            'fitting': 'Premium fittings and connectors for secure and leak-free pneumatic connections.',
            'filter': 'Industrial-grade filtration systems to ensure clean air and fluid in your processes.',
            'regulator': 'Pressure regulators for maintaining consistent system pressure and protecting equipment.',
            'button': 'Control buttons and switches for machine operation and safety systems.',
            'solenoid': 'Electromagnetic solenoid valves for automated fluid and air control.',
            'push button': 'Manual control devices used to start, stop, or reset operations in industrial systems.',
        }

        name_lower = category_name.lower()
        for key, desc in descriptions.items():
            if key in name_lower:
                return desc

        return f'Explore our comprehensive range of {category_name} products for industrial automation and control systems.'

    def _get_breadcrumbs(self, category):
        """Generate breadcrumbs for category hierarchy"""
        breadcrumbs = []
        current = category

        # Build breadcrumb trail from current to root
        while current:
            breadcrumbs.insert(0, {
                'name': current.name,
                'id': current.id,
                'url': f'/category/{slug(current)}',
            })
            current = current.parent_id

        # Add home and categories breadcrumbs
        breadcrumbs.insert(0, {
            'name': 'Categories',
            'id': 0,
            'url': '/categories',
        })
        breadcrumbs.insert(0, {
            'name': 'Home',
            'id': 0,
            'url': '/',
        })

        return breadcrumbs













# from odoo import http
# from odoo.http import request
#
#
# class DynamicCategoryController(http.Controller):
#
#     @http.route(['/category/<int:category_id>'], type='http', auth="public", website=True, sitemap=True)
#     def category_detail(self, category_id, **kwargs):
#         """Render detailed category page with child categories"""
#
#         # Fetch the main category
#         category = request.env['product.public.category'].browse(category_id)
#
#         if not category.exists():
#             return request.not_found()
#
#         # Get child categories
#         child_categories = request.env['product.public.category'].search([
#             ('parent_id', '=', category_id)
#         ], order='sequence, name')
#
#         # Prepare main category data
#         main_category = {
#             'id': category.id,
#             'name': category.name,
#             'description': category.website_description or f"Explore our {category.name} collection",
#             'image_url': self._get_category_image(category),
#             'slug': self._generate_slug(category.name),
#             'breadcrumbs': self._get_breadcrumbs(category),
#         }
#
#         # Prepare child categories data
#         child_categories_data = []
#         for child in child_categories:
#             child_info = {
#                 'id': child.id,
#                 'name': child.name,
#                 'description': child.website_description or f"Explore our {child.name} collection",
#                 'image_url': self._get_category_image(child),
#                 'slug': self._generate_slug(child.name),
#                 'product_count': len(child.product_tmpl_ids),
#                 'url': f'/category/{child.id}',
#             }
#             child_categories_data.append(child_info)
#
#         values = {
#             'main_category': main_category,
#             'child_categories': child_categories_data,
#             'category_id': category_id,
#             'page_name': 'category_detail',
#         }
#
#         return request.render('dynamic_category.category_detail_template', values)
#
#     def _get_category_image(self, category):
#         """Get category image URL - prioritize cover_image, then image_1920"""
#         if category.cover_image:
#             return f'/web/image/product.public.category/{category.id}/cover_image'
#         elif category.image_1920:
#             return f'/web/image/product.public.category/{category.id}/image_1920'
#         return '/web/static/img/s_website_placeholder.png'
#
#     def _generate_slug(self, name):
#         """Generate URL-friendly slug from name"""
#         return name.lower().replace(' ', '-').replace('/', '-')
#
#     def _get_breadcrumbs(self, category):
#         """Generate breadcrumbs for category hierarchy"""
#         breadcrumbs = []
#         current = category
#
#         while current:
#             breadcrumbs.insert(0, {
#                 'name': current.name,
#                 'id': current.id,
#                 'url': f'/category/{current.id}' if current.parent_id else '/',
#             })
#             current = current.parent_id
#
#         # Add home breadcrumb
#         breadcrumbs.insert(0, {
#             'name': 'Home',
#             'id': 0,
#             'url': '/',
#         })
#
#         return breadcrumbs
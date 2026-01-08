from odoo import http
from odoo.http import request


class DynamicCategoryController(http.Controller):

    @http.route(['/category/<int:category_id>'], type='http', auth="public", website=True, sitemap=True)
    def category_detail(self, category_id, **kwargs):
        """Render detailed category page with child categories"""

        # Fetch the main category
        category = request.env['product.public.category'].browse(category_id)

        if not category.exists():
            return request.not_found()

        # Get child categories
        child_categories = request.env['product.public.category'].search([
            ('parent_id', '=', category_id)
        ], order='sequence, name')

        # Prepare main category data
        main_category = {
            'id': category.id,
            'name': category.name,
            'description': category.website_description or f"Explore our {category.name} collection",
            'image_url': self._get_category_image(category),
            'slug': self._generate_slug(category.name),
            'breadcrumbs': self._get_breadcrumbs(category),
            'shop_url': f'/shop/category/{category.id}',  # Added shop URL with category filter
        }

        # Prepare child categories data
        child_categories_data = []
        for child in child_categories:
            child_info = {
                'id': child.id,
                'name': child.name,
                'description': child.website_description or f"Explore our {child.name} collection",
                'image_url': self._get_category_image(child),
                'slug': self._generate_slug(child.name),
                'product_count': len(child.product_tmpl_ids),
                'url': f'/category/{child.id}',
                'shop_url': f'/shop/category/{child.id}',  # Added shop URL for child categories
            }
            child_categories_data.append(child_info)

        values = {
            'main_category': main_category,
            'child_categories': child_categories_data,
            'category_id': category_id,
            'page_name': 'category_detail',
        }

        return request.render('dynamic_category.category_detail_template', values)

    def _get_category_image(self, category):
        """Get category image URL - prioritize cover_image, then image_1920"""
        if category.cover_image:
            return f'/web/image/product.public.category/{category.id}/cover_image'
        elif category.image_1920:
            return f'/web/image/product.public.category/{category.id}/image_1920'
        return '/web/static/img/s_website_placeholder.png'

    def _generate_slug(self, name):
        """Generate URL-friendly slug from name"""
        return name.lower().replace(' ', '-').replace('/', '-')

    def _get_breadcrumbs(self, category):
        """Generate breadcrumbs for category hierarchy"""
        breadcrumbs = []
        current = category

        while current:
            breadcrumbs.insert(0, {
                'name': current.name,
                'id': current.id,
                'url': f'/category/{current.id}' if current.parent_id else '/',
            })
            current = current.parent_id

        # Add home breadcrumb
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
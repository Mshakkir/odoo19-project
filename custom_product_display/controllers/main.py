from odoo import http
from odoo.addons.website_sale.controllers.main import WebsiteSale


class CustomWebsiteSale(WebsiteSale):

    @http.route()
    def shop(self, page=0, category=None, search='', min_price=0.0, max_price=0.0, ppg=False, **post):
        response = super().shop(
            page=page, category=category, search=search,
            min_price=min_price, max_price=max_price, ppg=ppg, **post
        )

        website = http.request.website

        # Simple method - get some products
        products = http.request.env['product.product'].search([
            ('sale_ok', '=', True),
            ('website_published', '=', True),
        ], limit=12)

        # Format data for template
        product_data = []
        for product in products:
            product_data.append({
                'product': product,
                'price': product.list_price,
                'qty_available': product.qty_available or 0,
                'image_url': '/web/image/product.product/%s/image_1024' % product.id if product.image_1920 else '/website/static/src/img/product_image_placeholder.svg',
            })

        if response.qcontext:
            response.qcontext['products_with_inventory'] = product_data

        return response




# from odoo import http
# from odoo.addons.website_sale.controllers.main import WebsiteSale
#
#
# class CustomWebsiteSale(WebsiteSale):
#
#     @http.route()
#     def shop(self, page=0, category=None, search='', min_price=0.0, max_price=0.0, ppg=False, **post):
#         response = super().shop(
#             page=page, category=category, search=search,
#             min_price=min_price, max_price=max_price, ppg=ppg, **post
#         )
#
#         # Get products with inventory using safe method
#         website = http.request.website
#         products_with_inventory = website.get_products_with_inventory_safe(limit=100)
#
#         if response.qcontext:
#             response.qcontext['products_with_inventory'] = products_with_inventory
#
#         return response
#
#
#
#
#
#
#
#
# # from odoo import http
# # from odoo.addons.website_sale.controllers.main import WebsiteSale
# #
# #
# # class CustomWebsiteSale(WebsiteSale):
# #
# #     @http.route()
# #     def shop(self, page=0, category=None, search='', min_price=0.0, max_price=0.0, ppg=False, **post):
# #         response = super().shop(
# #             page=page, category=category, search=search,
# #             min_price=min_price, max_price=max_price, ppg=ppg, **post
# #         )
# #
# #         # Add inventory data to response
# #         if response.qcontext and 'products' in response.qcontext:
# #             website = http.request.website
# #             products_with_inventory = website.get_products_with_inventory(limit=100)
# #             response.qcontext['products_with_inventory'] = products_with_inventory
# #
# #         return response
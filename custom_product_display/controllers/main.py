from odoo import http
from odoo.addons.website_sale.controllers.main import WebsiteSale


class CustomWebsiteSale(WebsiteSale):

    @http.route()
    def shop(self, page=0, category=None, search='', min_price=0.0, max_price=0.0, ppg=False, **post):
        response = super().shop(
            page=page, category=category, search=search,
            min_price=min_price, max_price=max_price, ppg=ppg, **post
        )

        # Get products with inventory
        website = http.request.website

        # Make sure this method exists in your model
        # It should be either get_products_with_inventory() or get_products_with_inventory_safe()
        # Choose ONE and be consistent

        # Option 1: If your model has get_products_with_inventory()
        products_with_inventory = website.get_products_with_inventory(limit=100)

        # Option 2: If your model has get_products_with_inventory_safe()
        # products_with_inventory = website.get_products_with_inventory_safe(limit=100)

        if response.qcontext and products_with_inventory:
            response.qcontext['products_with_inventory'] = products_with_inventory

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
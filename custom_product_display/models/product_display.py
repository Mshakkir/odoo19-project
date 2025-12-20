from odoo import models


class Website(models.Model):
    _inherit = 'website'

    # Method 1: Basic method
    def get_products_with_inventory(self, limit=50):
        """Get products for website display"""
        products = self.env['product.product'].search([
            ('sale_ok', '=', True),
            ('website_published', '=', True),
        ], limit=limit)

        product_data = []
        for product in products:
            product_data.append({
                'product': product,
                'price': product.list_price,
                'qty_available': product.qty_available or 0,
                'image_url': '/web/image/product.product/%s/image_1024' % product.id if product.image_1920 else '/website/static/src/img/product_image_placeholder.svg',
            })

        return product_data

    # Method 2: Safe method (alias)
    def get_products_with_inventory_safe(self, limit=50):
        """Alias for compatibility"""
        return self.get_products_with_inventory(limit=limit)








# from odoo import models, fields, api
#
#
# class ProductProduct(models.Model):
#     _inherit = 'product.product'
#
#     def get_inventory_details_safe(self):
#         """Safe method for public users - uses sudo() to avoid permission errors"""
#         self.ensure_one()
#
#         # Use sudo() to bypass permission checks for public data
#         product_sudo = self.sudo()
#
#         # Get basic quantity available (this field is usually accessible)
#         total_qty = product_sudo.qty_available or 0
#
#         # Simplified location info without deep stock queries
#         location_info = []
#         if total_qty > 0:
#             location_info.append({
#                 'location': 'Available',
#                 'quantity': total_qty,
#             })
#
#         return {
#             'total_quantity': total_qty,
#             'locations': location_info,
#             'has_inventory': total_qty > 0,
#             'product_name': self.name,
#             'default_code': self.default_code or '',
#         }
#
#
# class Website(models.Model):
#     _inherit = 'website'
#
#     def get_products_with_inventory_safe(self, limit=50):
#         """Safe method for website display - uses sudo()"""
#         # Use sudo() for the search to avoid permission issues
#         products = self.env['product.product'].sudo().search([
#             ('sale_ok', '=', True),
#             ('website_published', '=', True),
#             ('active', '=', True),
#         ], limit=limit)
#
#         product_data = []
#         for product in products:
#             # Use the safe method
#             inventory_data = product.get_inventory_details_safe()
#
#             product_data.append({
#                 'product': product,
#                 'inventory': inventory_data,
#                 'price': product.list_price,
#                 'currency': self.env.company.currency_id,
#                 'image_url': '/web/image/product.product/%s/image_1024' % product.id if product.image_1920 else '/website/static/src/img/product_image_placeholder.svg',
#             })
#
#         return product_data

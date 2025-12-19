from odoo import models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def get_inventory_details_safe(self):
        """Safe method that doesn't require stock permissions"""
        self.ensure_one()

        # Use fields that are accessible to all users
        total_qty = self.qty_available  # This is usually accessible

        return {
            'total_quantity': total_qty or 0,
            'has_inventory': total_qty > 0 if total_qty else False,
            'product_name': self.name,
            'default_code': self.default_code or '',
            'on_hand': total_qty or 0,
        }


class Website(models.Model):
    _inherit = 'website'

    def get_products_with_inventory_safe(self, limit=50):
        """Safe method for website display"""
        products = self.env['product.product'].search([
            ('sale_ok', '=', True),
            ('website_published', '=', True),
            ('active', '=', True),
        ], limit=limit)

        product_data = []
        for product in products.sudo():  # Use sudo for safe access
            product_data.append({
                'product': product,
                'inventory': {
                    'total_quantity': product.qty_available or 0,
                    'has_inventory': (product.qty_available or 0) > 0,
                },
                'price': product.list_price,
                'currency': self.env.company.currency_id,
                'image_url': '/web/image/product.product/%s/image_1024' % product.id if product.image_1920 else '/website/static/src/img/product_image_placeholder.svg',
            })

        return product_data











# from odoo import models, fields, api
#
#
# class ProductProduct(models.Model):
#     _inherit = 'product.product'
#
#     def get_inventory_details(self):
#         """Get inventory details for the product"""
#         self.ensure_one()
#
#         # Get available quantity
#         total_qty = self.qty_available
#
#         # Get locations with stock
#         quants = self.env['stock.quant'].search([
#             ('product_id', '=', self.id),
#             ('quantity', '>', 0)
#         ])
#
#         locations = []
#         for quant in quants:
#             locations.append({
#                 'location': quant.location_id.complete_name,
#                 'quantity': quant.quantity,
#                 'lot_name': quant.lot_id.name if quant.lot_id else None,
#             })
#
#         return {
#             'total_quantity': total_qty,
#             'locations': locations[:5],  # Limit to 5 locations
#             'has_inventory': total_qty > 0,
#             'product_name': self.name,
#             'default_code': self.default_code or '',
#             'barcode': self.barcode or '',
#             'categ_name': self.categ_id.name if self.categ_id else '',
#         }
#
#
# class Website(models.Model):
#     _inherit = 'website'
#
#     def get_products_with_inventory(self, limit=50):
#         """Get products with inventory details"""
#         products = self.env['product.product'].search([
#             ('sale_ok', '=', True),
#             ('website_published', '=', True),
#         ], limit=limit)
#
#         product_data = []
#         for product in products:
#             inventory_data = product.get_inventory_details()
#             # Optional: Filter only products with inventory
#             # if inventory_data['has_inventory']:
#             product_data.append({
#                 'product': product,
#                 'inventory': inventory_data,
#                 'price': product.list_price,
#                 'currency': self.env.company.currency_id,
#                 'image_url': '/web/image/product.product/%s/image_1024' % product.id if product.image_1920 else '/website/static/src/img/product_image_placeholder.svg',
#             })
#
#         return product_data
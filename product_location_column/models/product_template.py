# File: product_location_column/models/product_template.py

from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Quantity fields for each warehouse
    qty_wh_stock = fields.Float(
        string='WH/Stock',
        compute='_compute_warehouse_quantities',
        digits='Product Unit of Measure',
        store=False,
    )

    qty_dw_stock = fields.Float(
        string='DW/Stock',
        compute='_compute_warehouse_quantities',
        digits='Product Unit of Measure',
        store=False,
    )

    qty_balad_stock = fields.Float(
        string='Balad/Stock',
        compute='_compute_warehouse_quantities',
        digits='Product Unit of Measure',
        store=False,
    )

    @api.depends('qty_available')
    def _compute_warehouse_quantities(self):
        for product in self:
            product.qty_wh_stock = 0.0
            product.qty_dw_stock = 0.0
            product.qty_balad_stock = 0.0

            # Get all quants for this product
            quants = self.env['stock.quant'].search([
                ('product_id', 'in', product.product_variant_ids.ids),
                ('location_id.usage', '=', 'internal'),
            ])

            for quant in quants:
                location_name = quant.location_id.complete_name or ''

                # Check which warehouse this location belongs to
                if 'WH/Stock' in location_name or location_name.startswith('WH/'):
                    product.qty_wh_stock += quant.quantity
                elif 'DW/Stock' in location_name or location_name.startswith('DW/'):
                    product.qty_dw_stock += quant.quantity
                elif 'Balad/Stock' in location_name or location_name.startswith('Balad/'):
                    product.qty_balad_stock += quant.quantity


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # Quantity fields for each warehouse
    qty_wh_stock = fields.Float(
        string='WH/Stock',
        compute='_compute_warehouse_quantities_variant',
        digits='Product Unit of Measure',
        store=False,
    )

    qty_dw_stock = fields.Float(
        string='DW/Stock',
        compute='_compute_warehouse_quantities_variant',
        digits='Product Unit of Measure',
        store=False,
    )

    qty_balad_stock = fields.Float(
        string='Balad/Stock',
        compute='_compute_warehouse_quantities_variant',
        digits='Product Unit of Measure',
        store=False,
    )

    @api.depends('qty_available')
    def _compute_warehouse_quantities_variant(self):
        for product in self:
            product.qty_wh_stock = 0.0
            product.qty_dw_stock = 0.0
            product.qty_balad_stock = 0.0

            # Get all quants for this product variant
            quants = self.env['stock.quant'].search([
                ('product_id', '=', product.id),
                ('location_id.usage', '=', 'internal'),
            ])

            for quant in quants:
                location_name = quant.location_id.complete_name or ''

                # Check which warehouse this location belongs to
                if 'WH/Stock' in location_name or location_name.startswith('WH/'):
                    product.qty_wh_stock += quant.quantity
                elif 'DW/Stock' in location_name or location_name.startswith('DW/'):
                    product.qty_dw_stock += quant.quantity
                elif 'Balad/Stock' in location_name or location_name.startswith('Balad/'):
                    product.qty_balad_stock += quant.quantity









# # File: product_location_column/models/product_template.py
#
# from odoo import models, fields, api
#
#
# class ProductTemplate(models.Model):
#     _inherit = 'product.template'
#
#     stock_location_ids = fields.Many2many(
#         comodel_name='stock.location',
#         string='Stock Locations',
#         compute='_compute_stock_locations',
#         store=False,
#     )
#
#     stock_location_names = fields.Char(
#         string='Warehouse Locations',
#         compute='_compute_stock_locations',
#         store=False,
#     )
#
#     @api.depends('qty_available')
#     def _compute_stock_locations(self):
#         for product in self:
#             # Get all quants for this product with positive quantity
#             quants = self.env['stock.quant'].search([
#                 ('product_id', 'in', product.product_variant_ids.ids),
#                 ('quantity', '>', 0),
#                 ('location_id.usage', '=', 'internal'),
#             ])
#
#             locations = quants.mapped('location_id')
#             product.stock_location_ids = locations
#
#             if locations:
#                 product.stock_location_names = ', '.join(
#                     locations.mapped('complete_name')
#                 )
#             else:
#                 product.stock_location_names = 'No Stock'
#
#
# class ProductProduct(models.Model):
#     _inherit = 'product.product'
#
#     stock_location_ids = fields.Many2many(
#         comodel_name='stock.location',
#         string='Stock Locations',
#         compute='_compute_stock_locations_variant',
#         store=False,
#     )
#
#     stock_location_names = fields.Char(
#         string='Warehouse Locations',
#         compute='_compute_stock_locations_variant',
#         store=False,
#     )
#
#     @api.depends('qty_available')
#     def _compute_stock_locations_variant(self):
#         for product in self:
#             # Get all quants for this product variant with positive quantity
#             quants = self.env['stock.quant'].search([
#                 ('product_id', '=', product.id),
#                 ('quantity', '>', 0),
#                 ('location_id.usage', '=', 'internal'),
#             ])
#
#             locations = quants.mapped('location_id')
#             product.stock_location_ids = locations
#
#             if locations:
#                 product.stock_location_names = ', '.join(
#                     locations.mapped('complete_name')
#                 )
#             else:
#                 product.stock_location_names = 'No Stock'
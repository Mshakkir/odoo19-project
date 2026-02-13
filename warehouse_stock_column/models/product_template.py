from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    qty_fyh_stock = fields.Float(
        string='FYH/Stock',
        compute='_compute_warehouse_quantities',
        digits='Product Unit of Measure',
        store=True,
    )
    qty_bld_stock = fields.Float(
        string='BLD/Stock',
        compute='_compute_warehouse_quantities',
        digits='Product Unit of Measure',
        store=True,
    )
    qty_dmm_stock = fields.Float(
        string='DMM-1/Stock',
        compute='_compute_warehouse_quantities',
        digits='Product Unit of Measure',
        store=True,
    )

    total_sales_price = fields.Float(
        string='Total Sales Price',
        compute='_compute_total_prices',
        digits='Product Price',
        store=True,
        help='Sales Price × On Hand Quantity'
    )

    total_cost_price = fields.Float(
        string='Total Cost Price',
        compute='_compute_total_prices',
        digits='Product Price',
        store=True,
        help='Cost × On Hand Quantity'
    )

    @api.depends('product_variant_ids', 'product_variant_ids.stock_quant_ids',
                 'product_variant_ids.stock_quant_ids.quantity', 'product_variant_ids.stock_quant_ids.location_id')
    def _compute_warehouse_quantities(self):
        for product in self:
            qty_fyh = 0.0
            qty_bld = 0.0
            qty_dmm = 0.0

            if product.product_variant_ids:
                quants = self.env['stock.quant'].sudo().search([
                    ('product_id', 'in', product.product_variant_ids.ids),
                    ('location_id.usage', '=', 'internal'),
                ])

                for quant in quants:
                    loc_name = quant.location_id.complete_name or ''
                    loc_name_upper = loc_name.upper()

                    # Match warehouse location names from your system
                    if 'FYH/' in loc_name_upper or loc_name_upper.startswith('FYH'):
                        qty_fyh += quant.quantity
                    elif 'BLD/' in loc_name_upper or loc_name_upper.startswith('BLD'):
                        qty_bld += quant.quantity
                    elif 'DMM-1/' in loc_name_upper or loc_name_upper.startswith('DMM-1'):
                        qty_dmm += quant.quantity

            product.qty_fyh_stock = qty_fyh
            product.qty_bld_stock = qty_bld
            product.qty_dmm_stock = qty_dmm

    @api.depends('list_price', 'standard_price', 'qty_available')
    def _compute_total_prices(self):
        for product in self:
            # Total Sales Price = Sales Price (list_price) × On Hand Quantity (qty_available)
            product.total_sales_price = product.list_price * product.qty_available

            # Total Cost Price = Cost (standard_price) × On Hand Quantity (qty_available)
            product.total_cost_price = product.standard_price * product.qty_available


class ProductProduct(models.Model):
    _inherit = 'product.product'

    qty_fyh_stock = fields.Float(
        string='FYH/Stock',
        compute='_compute_warehouse_quantities_variant',
        digits='Product Unit of Measure',
        store=True,
    )
    qty_bld_stock = fields.Float(
        string='BLD/Stock',
        compute='_compute_warehouse_quantities_variant',
        digits='Product Unit of Measure',
        store=True,
    )
    qty_dmm_stock = fields.Float(
        string='DMM-1/Stock',
        compute='_compute_warehouse_quantities_variant',
        digits='Product Unit of Measure',
        store=True,
    )

    total_sales_price = fields.Float(
        string='Total Sales Price',
        compute='_compute_total_prices_variant',
        digits='Product Price',
        store=True,
        help='Sales Price × On Hand Quantity'
    )

    total_cost_price = fields.Float(
        string='Total Cost Price',
        compute='_compute_total_prices_variant',
        digits='Product Price',
        store=True,
        help='Cost × On Hand Quantity'
    )

    @api.depends('stock_quant_ids', 'stock_quant_ids.quantity', 'stock_quant_ids.location_id')
    def _compute_warehouse_quantities_variant(self):
        for product in self:
            qty_fyh = 0.0
            qty_bld = 0.0
            qty_dmm = 0.0

            quants = self.env['stock.quant'].sudo().search([
                ('product_id', '=', product.id),
                ('location_id.usage', '=', 'internal'),
            ])

            for quant in quants:
                loc_name = quant.location_id.complete_name or ''
                loc_name_upper = loc_name.upper()

                # Match warehouse location names from your system
                if 'FYH/' in loc_name_upper or loc_name_upper.startswith('FYH'):
                    qty_fyh += quant.quantity
                elif 'BLD/' in loc_name_upper or loc_name_upper.startswith('BLD'):
                    qty_bld += quant.quantity
                elif 'DMM-1/' in loc_name_upper or loc_name_upper.startswith('DMM-1'):
                    qty_dmm += quant.quantity

            product.qty_fyh_stock = qty_fyh
            product.qty_bld_stock = qty_bld
            product.qty_dmm_stock = qty_dmm

    @api.depends('lst_price', 'standard_price', 'qty_available')
    def _compute_total_prices_variant(self):
        for product in self:
            # Total Sales Price = Sales Price (lst_price) × On Hand Quantity (qty_available)
            product.total_sales_price = product.lst_price * product.qty_available

            # Total Cost Price = Cost (standard_price) × On Hand Quantity (qty_available)
            product.total_cost_price = product.standard_price * product.qty_available













# from odoo import models, fields, api
#
#
# class ProductTemplate(models.Model):
#     _inherit = 'product.template'
#
#     qty_fyh_stock = fields.Float(
#         string='FYH/Stock',
#         compute='_compute_warehouse_quantities',
#         digits='Product Unit of Measure',
#         store=True,
#     )
#     qty_bld_stock = fields.Float(
#         string='BLD/Stock',
#         compute='_compute_warehouse_quantities',
#         digits='Product Unit of Measure',
#         store=True,
#     )
#     qty_dmm_stock = fields.Float(
#         string='DMM-1/Stock',
#         compute='_compute_warehouse_quantities',
#         digits='Product Unit of Measure',
#         store=True,
#     )
#
#     @api.depends('product_variant_ids', 'product_variant_ids.stock_quant_ids',
#                  'product_variant_ids.stock_quant_ids.quantity', 'product_variant_ids.stock_quant_ids.location_id')
#     def _compute_warehouse_quantities(self):
#         for product in self:
#             qty_fyh = 0.0
#             qty_bld = 0.0
#             qty_dmm = 0.0
#
#             if product.product_variant_ids:
#                 quants = self.env['stock.quant'].sudo().search([
#                     ('product_id', 'in', product.product_variant_ids.ids),
#                     ('location_id.usage', '=', 'internal'),
#                 ])
#
#                 for quant in quants:
#                     loc_name = quant.location_id.complete_name or ''
#                     loc_name_upper = loc_name.upper()
#
#                     # Match warehouse location names from your system
#                     if 'FYH/' in loc_name_upper or loc_name_upper.startswith('FYH'):
#                         qty_fyh += quant.quantity
#                     elif 'BLD/' in loc_name_upper or loc_name_upper.startswith('BLD'):
#                         qty_bld += quant.quantity
#                     elif 'DMM-1/' in loc_name_upper or loc_name_upper.startswith('DMM-1'):
#                         qty_dmm += quant.quantity
#
#             product.qty_fyh_stock = qty_fyh
#             product.qty_bld_stock = qty_bld
#             product.qty_dmm_stock = qty_dmm
#
#
# class ProductProduct(models.Model):
#     _inherit = 'product.product'
#
#     qty_fyh_stock = fields.Float(
#         string='FYH/Stock',
#         compute='_compute_warehouse_quantities_variant',
#         digits='Product Unit of Measure',
#         store=True,
#     )
#     qty_bld_stock = fields.Float(
#         string='BLD/Stock',
#         compute='_compute_warehouse_quantities_variant',
#         digits='Product Unit of Measure',
#         store=True,
#     )
#     qty_dmm_stock = fields.Float(
#         string='DMM-1/Stock',
#         compute='_compute_warehouse_quantities_variant',
#         digits='Product Unit of Measure',
#         store=True,
#     )
#
#     @api.depends('stock_quant_ids', 'stock_quant_ids.quantity', 'stock_quant_ids.location_id')
#     def _compute_warehouse_quantities_variant(self):
#         for product in self:
#             qty_fyh = 0.0
#             qty_bld = 0.0
#             qty_dmm = 0.0
#
#             quants = self.env['stock.quant'].sudo().search([
#                 ('product_id', '=', product.id),
#                 ('location_id.usage', '=', 'internal'),
#             ])
#
#             for quant in quants:
#                 loc_name = quant.location_id.complete_name or ''
#                 loc_name_upper = loc_name.upper()
#
#                 # Match warehouse location names from your system
#                 if 'FYH/' in loc_name_upper or loc_name_upper.startswith('FYH'):
#                     qty_fyh += quant.quantity
#                 elif 'BLD/' in loc_name_upper or loc_name_upper.startswith('BLD'):
#                     qty_bld += quant.quantity
#                 elif 'DMM-1/' in loc_name_upper or loc_name_upper.startswith('DMM-1'):
#                     qty_dmm += quant.quantity
#
#             product.qty_fyh_stock = qty_fyh
#             product.qty_bld_stock = qty_bld
#             product.qty_dmm_stock = qty_dmm
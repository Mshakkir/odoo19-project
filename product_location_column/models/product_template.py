# File: product_location_column/models/product_template.py

from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    stock_location_ids = fields.Many2many(
        comodel_name='stock.location',
        string='Stock Locations',
        compute='_compute_stock_locations',
        store=False,
    )

    stock_location_names = fields.Char(
        string='Warehouse Locations',
        compute='_compute_stock_locations',
        store=False,
    )

    @api.depends('qty_available')
    def _compute_stock_locations(self):
        for product in self:
            # Get all quants for this product with positive quantity
            quants = self.env['stock.quant'].search([
                ('product_id', 'in', product.product_variant_ids.ids),
                ('quantity', '>', 0),
                ('location_id.usage', '=', 'internal'),
            ])

            locations = quants.mapped('location_id')
            product.stock_location_ids = locations

            if locations:
                product.stock_location_names = ', '.join(
                    locations.mapped('complete_name')
                )
            else:
                product.stock_location_names = 'No Stock'


class ProductProduct(models.Model):
    _inherit = 'product.product'

    stock_location_ids = fields.Many2many(
        comodel_name='stock.location',
        string='Stock Locations',
        compute='_compute_stock_locations_variant',
        store=False,
    )

    stock_location_names = fields.Char(
        string='Warehouse Locations',
        compute='_compute_stock_locations_variant',
        store=False,
    )

    @api.depends('qty_available')
    def _compute_stock_locations_variant(self):
        for product in self:
            # Get all quants for this product variant with positive quantity
            quants = self.env['stock.quant'].search([
                ('product_id', '=', product.id),
                ('quantity', '>', 0),
                ('location_id.usage', '=', 'internal'),
            ])

            locations = quants.mapped('location_id')
            product.stock_location_ids = locations

            if locations:
                product.stock_location_names = ', '.join(
                    locations.mapped('complete_name')
                )
            else:
                product.stock_location_names = 'No Stock'
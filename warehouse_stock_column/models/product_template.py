from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    qty_wh_stock = fields.Float(
        string='WH/Stock',
        compute='_compute_warehouse_quantities',
        digits='Product Unit of Measure',
        store=True,
    )
    qty_dw_stock = fields.Float(
        string='DW/Stock',
        compute='_compute_warehouse_quantities',
        digits='Product Unit of Measure',
        store=True,
    )
    qty_balad_stock = fields.Float(
        string='Balad/Stock',
        compute='_compute_warehouse_quantities',
        digits='Product Unit of Measure',
        store=True,
    )

    @api.depends('product_variant_ids', 'product_variant_ids.stock_quant_ids',
                 'product_variant_ids.stock_quant_ids.quantity', 'product_variant_ids.stock_quant_ids.location_id')
    def _compute_warehouse_quantities(self):
        for product in self:
            qty_wh = 0.0
            qty_dw = 0.0
            qty_balad = 0.0

            if product.product_variant_ids:
                quants = self.env['stock.quant'].sudo().search([
                    ('product_id', 'in', product.product_variant_ids.ids),
                    ('location_id.usage', '=', 'internal'),
                ])

                for quant in quants:
                    loc_name = quant.location_id.complete_name or ''
                    loc_name_upper = loc_name.upper()

                    # Match your actual location names
                    if 'MAIN/' in loc_name_upper or loc_name_upper.startswith('MAIN'):
                        qty_wh += quant.quantity
                    elif 'DAMMA/' in loc_name_upper or loc_name_upper.startswith('DAMMA'):
                        qty_dw += quant.quantity
                    elif 'BALAD/' in loc_name_upper or loc_name_upper.startswith('BALAD'):
                        qty_balad += quant.quantity

            product.qty_wh_stock = qty_wh
            product.qty_dw_stock = qty_dw
            product.qty_balad_stock = qty_balad


class ProductProduct(models.Model):
    _inherit = 'product.product'

    qty_wh_stock = fields.Float(
        string='WH/Stock',
        compute='_compute_warehouse_quantities_variant',
        digits='Product Unit of Measure',
        store=True,
    )
    qty_dw_stock = fields.Float(
        string='DW/Stock',
        compute='_compute_warehouse_quantities_variant',
        digits='Product Unit of Measure',
        store=True,
    )
    qty_balad_stock = fields.Float(
        string='Balad/Stock',
        compute='_compute_warehouse_quantities_variant',
        digits='Product Unit of Measure',
        store=True,
    )

    @api.depends('stock_quant_ids', 'stock_quant_ids.quantity', 'stock_quant_ids.location_id')
    def _compute_warehouse_quantities_variant(self):
        for product in self:
            qty_wh = 0.0
            qty_dw = 0.0
            qty_balad = 0.0

            quants = self.env['stock.quant'].sudo().search([
                ('product_id', '=', product.id),
                ('location_id.usage', '=', 'internal'),
            ])

            for quant in quants:
                loc_name = quant.location_id.complete_name or ''
                loc_name_upper = loc_name.upper()

                # Match your actual location names
                if 'MAIN/' in loc_name_upper or loc_name_upper.startswith('MAIN'):
                    qty_wh += quant.quantity
                elif 'DAMMA/' in loc_name_upper or loc_name_upper.startswith('DAMMA'):
                    qty_dw += quant.quantity
                elif 'BALAD/' in loc_name_upper or loc_name_upper.startswith('BALAD'):
                    qty_balad += quant.quantity

            product.qty_wh_stock = qty_wh
            product.qty_dw_stock = qty_dw
            product.qty_balad_stock = qty_balad
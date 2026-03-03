from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    x_created_date = fields.Date(
        string='Created Date',
        readonly=True,
        copy=False,
        default=fields.Date.today,
        help='Date when this product was created. Auto-filled on creation.',
    )

    x_created_date_display = fields.Char(
        string='Created Date',
        compute='_compute_created_date_display',
        store=True,
    )

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
        help='Sales Price x On Hand Quantity'
    )

    total_cost_price = fields.Float(
        string='Total Cost Price',
        compute='_compute_total_prices',
        digits='Product Price',
        store=True,
        help='Cost x On Hand Quantity'
    )

    @api.depends('x_created_date')
    def _compute_created_date_display(self):
        for product in self:
            if product.x_created_date:
                product.x_created_date_display = product.x_created_date.strftime('%d/%m/%y')
            else:
                product.x_created_date_display = ''

    @api.model_create_multi
    def create(self, vals_list):
        today = fields.Date.context_today(self)
        for vals in vals_list:
            if not vals.get('x_created_date'):
                vals['x_created_date'] = today
        return super().create(vals_list)

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
            product.total_sales_price = product.list_price * product.qty_available
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
        help='Sales Price x On Hand Quantity'
    )

    total_cost_price = fields.Float(
        string='Total Cost Price',
        compute='_compute_total_prices_variant',
        digits='Product Price',
        store=True,
        help='Cost x On Hand Quantity'
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
            product.total_sales_price = product.lst_price * product.qty_available
            product.total_cost_price = product.standard_price * product.qty_available
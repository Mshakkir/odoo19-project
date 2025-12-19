from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Add custom fields if needed
    highlight = fields.Boolean('Highlight Product', default=False)
    custom_description = fields.Html('Custom Website Description')

    @api.depends('product_variant_ids', 'product_variant_ids.stock_quant_ids')
    def _compute_total_qty(self):
        for product in self:
            total = sum(
                product.product_variant_ids.mapped(
                    lambda v: v.with_context(warehouse=False).qty_available
                )
            )
            product.total_qty_available = total

    total_qty_available = fields.Integer(
        'Total Qty Available',
        compute='_compute_total_qty',
        store=True
    )

    def get_inventory_status(self):
        """Get inventory status for display"""
        if self.total_qty_available == 0:
            return 'out_of_stock'
        elif self.total_qty_available < 10:
            return 'low_stock'
        else:
            return 'in_stock'


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.depends('stock_quant_ids')
    def _compute_qty_available(self):
        """Calculate available quantity from inventory"""
        for product in self:
            qty = product.with_context(warehouse=False).qty_available
            product.qty_available = qty

    qty_available = fields.Integer(
        'Quantity Available',
        compute='_compute_qty_available',
        store=True
    )
from odoo import models, api

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.onchange('product_id')
    def _onchange_product_id_set_location(self):
        if self.product_id and self.product_id.product_tmpl_id.default_location_id:
            # This will be used when creating stock moves
            self.location_id = self.product_id.product_tmpl_id.default_location_id.id
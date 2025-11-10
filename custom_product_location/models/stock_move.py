from odoo import models, api


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.model
    def create(self, vals):
        # Get product and set default location if available
        if vals.get('product_id'):
            product = self.env['product.product'].browse(vals['product_id'])
            if product.product_tmpl_id.default_location_id:
                # For incoming moves (purchases), set destination location
                if vals.get('location_dest_id'):
                    picking = self.env['stock.picking'].browse(vals.get('picking_id'))
                    if picking and picking.picking_type_id.code == 'incoming':
                        vals['location_dest_id'] = product.product_tmpl_id.default_location_id.id

                # For outgoing moves (sales/deliveries), set source location
                if vals.get('location_id'):
                    picking = self.env['stock.picking'].browse(vals.get('picking_id'))
                    if picking and picking.picking_type_id.code == 'outgoing':
                        vals['location_id'] = product.product_tmpl_id.default_location_id.id

        return super(StockMove, self).create(vals)
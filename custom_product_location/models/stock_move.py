from odoo import models, api


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.model_create_multi
    def create(self, vals_list):
        # Handle both single dict and list of dicts
        if not isinstance(vals_list, list):
            vals_list = [vals_list]

        for vals in vals_list:
            if vals.get('product_id'):
                product = self.env['product.product'].browse(vals['product_id'])
                default_location = product.product_tmpl_id.default_location_id

                if default_location:
                    # Check picking type to determine which location to update
                    picking_id = vals.get('picking_id')
                    if picking_id:
                        picking = self.env['stock.picking'].browse(picking_id)

                        # For incoming moves (Purchase/Receipt)
                        if picking.picking_type_id.code == 'incoming':
                            vals['location_dest_id'] = default_location.id

                        # For outgoing moves (Sales/Delivery)
                        elif picking.picking_type_id.code == 'outgoing':
                            vals['location_id'] = default_location.id

        return super(StockMove, self).create(vals_list)
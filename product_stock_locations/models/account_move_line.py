from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model
    def get_product_stock_locations(self, product_id):
        """
        Fetch stock availability by location for a given product.
        Returns list of internal locations with on_hand, reserved, and available qty.
        """
        if not product_id:
            return []

        # Search stock quants for this product in internal locations
        quants = self.env['stock.quant'].search([
            ('product_id', '=', product_id),
            ('location_id.usage', '=', 'internal'),
        ])

        result = []
        total_onhand = 0.0
        total_reserved = 0.0

        for quant in quants:
            on_hand = quant.quantity
            reserved = quant.reserved_quantity
            available = on_hand - reserved

            # Skip locations with zero or negative stock
            if on_hand <= 0:
                continue

            total_onhand += on_hand
            total_reserved += reserved

            result.append({
                'id': quant.id,
                'location_id': quant.location_id.id,
                'location_name': quant.location_id.complete_name or quant.location_id.name,
                'on_hand': on_hand,
                'reserved': reserved,
                'available': available,
                'uom': quant.product_uom_id.name if quant.product_uom_id else '',
                'lot_name': quant.lot_id.name if quant.lot_id else '',
                'package_name': quant.package_id.name if quant.package_id else '',
            })

        # Sort by location name
        result.sort(key=lambda x: x['location_name'])

        # Add totals row at the end
        if result:
            result.append({
                'id': -1,
                'location_id': False,
                'location_name': 'TOTAL',
                'on_hand': total_onhand,
                'reserved': total_reserved,
                'available': total_onhand - total_reserved,
                'uom': result[0]['uom'] if result else '',
                'lot_name': '',
                'package_name': '',
            })

        return result
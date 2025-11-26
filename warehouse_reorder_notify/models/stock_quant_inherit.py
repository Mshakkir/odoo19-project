from odoo import models, fields, api
from odoo.exceptions import UserError

class StockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.model
    def check_reorder_notification(self):
        products = self.env['product.product'].search([])

        for product in products:
            for warehouse in self.env['stock.warehouse'].search([]):

                # Get quantity in each warehouse location
                qty = self.env['stock.quant']._get_available_quantity(
                    product, warehouse.lot_stock_id
                )

                # Read Min/Max Rule
                rule = self.env['stock.warehouse.orderpoint'].search([
                    ('product_id', '=', product.id),
                    ('warehouse_id', '=', warehouse.id),
                ], limit=1)

                if not rule:
                    continue

                # If quantity < minimum → create notification
                if qty < rule.product_min_qty:
                    existing = self.env['reorder.notification'].search([
                        ('product_id', '=', product.id),
                        ('warehouse_id', '=', warehouse.id),
                        ('state', '=', 'new'),
                    ])

                    if not existing:  # avoid duplicates
                        self.env['reorder.notification'].create({
                            'product_id': product.id,
                            'warehouse_id': warehouse.id,
                            'qty_on_hand': qty,
                            'min_qty': rule.product_min_qty,
                            'user_id': warehouse.user_ids[0].id
                                if warehouse.user_ids else None,
                        })

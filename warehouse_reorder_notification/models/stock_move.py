from odoo import models, api


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _action_done(self, cancel_backorder=False):
        """Override to auto-close notifications when goods are received"""
        result = super(StockMove, self)._action_done(cancel_backorder=cancel_backorder)

        # After stock move is done, check if any orderpoints need notification closure
        for move in self:
            if move.state == 'done' and move.location_dest_id.usage == 'internal':
                # This is an incoming stock move (purchase receipt, etc)
                product = move.product_id
                location = move.location_dest_id

                # Find orderpoints for this product and location
                orderpoints = self.env['stock.warehouse.orderpoint'].sudo().search([
                    ('product_id', '=', product.id),
                    ('location_id', '=', location.id),
                ])

                # Check and close notifications if stock is now OK
                for orderpoint in orderpoints:
                    orderpoint._auto_close_notifications_if_stock_ok()

        return result


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.model_create_multi
    def create(self, vals_list):
        """Override to auto-close notifications when stock quantity changes"""
        result = super(StockQuant, self).create(vals_list)

        # After quant is created, check orderpoints
        for quant in result:
            if quant.location_id.usage == 'internal':
                orderpoints = self.env['stock.warehouse.orderpoint'].sudo().search([
                    ('product_id', '=', quant.product_id.id),
                    ('location_id', '=', quant.location_id.id),
                ])

                for orderpoint in orderpoints:
                    orderpoint._auto_close_notifications_if_stock_ok()

        return result

    def write(self, vals):
        """Override to auto-close notifications when stock quantity updates"""
        result = super(StockQuant, self).write(vals)

        # After quant is updated, check orderpoints
        if 'quantity' in vals or 'reserved_quantity' in vals:
            for quant in self:
                if quant.location_id.usage == 'internal':
                    orderpoints = self.env['stock.warehouse.orderpoint'].sudo().search([
                        ('product_id', '=', quant.product_id.id),
                        ('location_id', '=', quant.location_id.id),
                    ])

                    for orderpoint in orderpoints:
                        orderpoint._auto_close_notifications_if_stock_ok()

        return result








# from odoo import models, api
#
#
# class StockMove(models.Model):
#     _inherit = 'stock.move'
#
#     def _action_done(self, cancel_backorder=False):
#         """Override to auto-close notifications when goods are received"""
#         result = super(StockMove, self)._action_done(cancel_backorder=cancel_backorder)
#
#         # After stock move is done, check if any orderpoints need notification closure
#         for move in self:
#             if move.state == 'done' and move.location_dest_id.usage == 'internal':
#                 # This is an incoming stock move (purchase receipt, etc)
#                 product = move.product_id
#                 location = move.location_dest_id
#
#                 # Find orderpoints for this product and location
#                 orderpoints = self.env['stock.warehouse.orderpoint'].sudo().search([
#                     ('product_id', '=', product.id),
#                     ('location_id', '=', location.id),
#                 ])
#
#                 # Check and close notifications if stock is now OK
#                 for orderpoint in orderpoints:
#                     orderpoint._auto_close_notifications_if_stock_ok()
#
#         return result
#
#
# class StockQuant(models.Model):
#     _inherit = 'stock.quant'
#
#     @api.model_create_multi
#     def create(self, vals_list):
#         """Override to auto-close notifications when stock quantity changes"""
#         result = super(StockQuant, self).create(vals_list)
#
#         # After quant is created, check orderpoints
#         for quant in result:
#             if quant.location_id.usage == 'internal':
#                 orderpoints = self.env['stock.warehouse.orderpoint'].sudo().search([
#                     ('product_id', '=', quant.product_id.id),
#                     ('location_id', '=', quant.location_id.id),
#                 ])
#
#                 for orderpoint in orderpoints:
#                     orderpoint._auto_close_notifications_if_stock_ok()
#
#         return result
#
#     def write(self, vals):
#         """Override to auto-close notifications when stock quantity updates"""
#         result = super(StockQuant, self).write(vals)
#
#         # After quant is updated, check orderpoints
#         if 'quantity' in vals or 'reserved_quantity' in vals:
#             for quant in self:
#                 if quant.location_id.usage == 'internal':
#                     orderpoints = self.env['stock.warehouse.orderpoint'].sudo().search([
#                         ('product_id', '=', quant.product_id.id),
#                         ('location_id', '=', quant.location_id.id),
#                     ])
#
#                     for orderpoint in orderpoints:
#                         orderpoint._auto_close_notifications_if_stock_ok()
#
#         return result
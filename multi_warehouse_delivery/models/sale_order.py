from odoo import models, fields, api, _
from collections import defaultdict


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Delivery Warehouse',
        help='Warehouse from which this product will be delivered',
        domain="[('company_id', '=', company_id)]",
        copy=False
    )

    @api.onchange('product_id')
    def _onchange_product_id_set_warehouse(self):
        """Auto-select warehouse with available stock"""
        if self.product_id and self.product_id.type == 'product':
            # Get warehouses with stock
            warehouses = self.env['stock.warehouse'].search([
                ('company_id', '=', self.company_id.id or self.env.company.id)
            ])

            for warehouse in warehouses:
                stock = self.product_id.with_context(
                    warehouse=warehouse.id
                ).qty_available

                if stock > 0:
                    self.warehouse_id = warehouse.id
                    return

            # If no stock found, use order's warehouse
            if self.order_id and self.order_id.warehouse_id:
                self.warehouse_id = self.order_id.warehouse_id

    def _prepare_procurement_values(self):
        """Override to use line-specific warehouse"""
        values = super(SaleOrderLine, self)._prepare_procurement_values()

        # Use line's warehouse if set
        if self.warehouse_id:
            values['warehouse_id'] = self.warehouse_id

        return values

    def _action_launch_stock_rule(self, previous_product_uom_qty=False):
        """
        Override to ensure pickings are confirmed one at a time
        """
        # Store context flag to prevent recursive interception
        if self.env.context.get('multi_warehouse_processing'):
            return super(SaleOrderLine, self)._action_launch_stock_rule(
                previous_product_uom_qty=previous_product_uom_qty
            )

        # Check if we have multiple warehouses
        warehouses = self.filtered(
            lambda l: l.product_id.type in ['product', 'consu'] and l.warehouse_id
        ).mapped('warehouse_id')

        if len(warehouses) <= 1:
            # Single warehouse - use standard flow
            return super(SaleOrderLine, self)._action_launch_stock_rule(
                previous_product_uom_qty=previous_product_uom_qty
            )

        # Multiple warehouses - we need to intercept the picking confirmation
        # Process lines with a special context that will catch the picking confirmation
        return super(SaleOrderLine, self.with_context(
            multi_warehouse_separate_confirm=True
        ))._action_launch_stock_rule(
            previous_product_uom_qty=previous_product_uom_qty
        )


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def action_confirm(self):
        """
        Override to handle batch confirmation when multiple warehouses are involved
        Confirm pickings one at a time to avoid singleton errors in other modules
        """
        # Check if we're in multi-warehouse mode and have multiple pickings
        if self.env.context.get('multi_warehouse_separate_confirm') and len(self) > 1:
            # Confirm each picking individually
            for picking in self:
                super(StockPicking, picking).action_confirm()
            return True
        else:
            # Standard confirmation
            return super(StockPicking, self).action_confirm()


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _create_delivery_line(self, carrier, price_unit):
        """Override to prevent issues with delivery lines"""
        result = super(SaleOrder, self)._create_delivery_line(carrier, price_unit)
        # Ensure delivery line gets a warehouse
        if result and not result.warehouse_id:
            result.warehouse_id = self.warehouse_id
        return result
# from odoo import controllers, fields, api, _
#
#
# class SaleOrderLine(controllers.Model):
#     _inherit = 'sale.order.line'
#
#     warehouse_id = fields.Many2one(
#         'stock.warehouse',
#         string='Delivery Warehouse',
#         help='Warehouse from which this product will be delivered',
#         domain="[('company_id', '=', company_id)]",
#         copy=False
#     )
#
#     @api.onchange('product_id')
#     def _onchange_product_id_set_warehouse(self):
#         """Auto-select warehouse with available stock"""
#         if self.product_id and self.product_id.type == 'product':
#             warehouses = self.env['stock.warehouse'].search([
#                 ('company_id', '=', self.company_id.id or self.env.company.id)
#             ])
#
#             for warehouse in warehouses:
#                 stock = self.product_id.with_context(
#                     warehouse=warehouse.id
#                 ).qty_available
#
#                 if stock > 0:
#                     self.warehouse_id = warehouse.id
#                     return
#
#             # Fallback to order's warehouse
#             if self.order_id and self.order_id.warehouse_id:
#                 self.warehouse_id = self.order_id.warehouse_id
#
#     def _prepare_procurement_values(self):
#         """Override to use line-specific warehouse"""
#         values = super()._prepare_procurement_values()
#
#         if self.warehouse_id:
#             values['warehouse_id'] = self.warehouse_id
#             # Also update route to use warehouse's routes
#             values['route_ids'] = self.warehouse_id.route_ids
#
#         return values
#
#
# class SaleOrder(controllers.Model):
#     _inherit = 'sale.order'
#
#     def _create_delivery_line(self, carrier, price_unit):
#         """Override to ensure delivery line gets a warehouse"""
#         result = super()._create_delivery_line(carrier, price_unit)
#
#         if result and not result.warehouse_id and self.warehouse_id:
#             result.warehouse_id = self.warehouse_id
#
#         return result
#
#     def _action_confirm(self):
#         """
#         Override to handle multiple warehouses properly.
#         This is safer than overriding action_confirm.
#         """
#         # Check if we have multiple warehouses
#         warehouses = self.order_line.filtered(
#             lambda l: l.product_id.type in ['product', 'consu'] and l.warehouse_id
#         ).mapped('warehouse_id')
#
#         if len(warehouses) > 1:
#             # Process with multi-warehouse context
#             return super(SaleOrder, self.with_context(
#                 multi_warehouse_mode=True
#             ))._action_confirm()
#
#         # Standard flow for single warehouse
#         return super()._action_confirm()
#
#
# class StockRule(controllers.Model):
#     _inherit = 'stock.rule'
#
#     def _get_stock_move_values(self, product_id, product_qty, product_uom,
#                                location_dest_id, name, origin, company_id, values):
#         """
#         Override to respect line-specific warehouse in move values.
#         This is safer than overriding picking creation.
#         """
#         move_values = super()._get_stock_move_values(
#             product_id, product_qty, product_uom,
#             location_dest_id, name, origin, company_id, values
#         )
#
#         # If we have a specific warehouse from sale line, use it
#         if values.get('warehouse_id') and self.env.context.get('multi_warehouse_mode'):
#             warehouse = values['warehouse_id']
#             if isinstance(warehouse, int):
#                 warehouse = self.env['stock.warehouse'].browse(warehouse)
#
#             # Update source location to warehouse's stock location
#             move_values['location_id'] = warehouse.lot_stock_id.id
#             move_values['warehouse_id'] = warehouse.id
#
#         return move_values
#
#
# class StockPicking(controllers.Model):
#     _inherit = 'stock.picking'
#
#     def action_confirm(self):
#         """
#         Safe override to handle batch confirmation in multi-warehouse scenarios.
#         Confirms pickings individually to avoid singleton errors.
#         """
#         if self.env.context.get('multi_warehouse_mode') and len(self) > 1:
#             # Confirm each picking individually to avoid singleton issues
#             for picking in self:
#                 super(StockPicking, picking).action_confirm()
#             return True
#
#         return super().action_confirm()
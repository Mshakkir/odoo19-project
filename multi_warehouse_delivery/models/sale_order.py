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
        """Override to use line-specific warehouse and its output location"""
        values = super(SaleOrderLine, self)._prepare_procurement_values()

        if self.warehouse_id:
            values['warehouse_id'] = self.warehouse_id
            # Force the source location to this warehouse's output/stock location
            # so the delivery note (picking) is created from the correct warehouse
            route_ids = self.warehouse_id.route_ids
            if route_ids:
                values['route_ids'] = route_ids

        return values

    def _action_launch_stock_rule(self, previous_product_uom_qty=False):
        """
        Override to group lines by warehouse and create one picking per warehouse
        with the correct source location.
        """
        if self.env.context.get('multi_warehouse_processing'):
            return super()._action_launch_stock_rule(
                previous_product_uom_qty=previous_product_uom_qty
            )

        warehouses = self.filtered(
            lambda l: l.product_id.type in ['product', 'consu'] and l.warehouse_id
        ).mapped('warehouse_id')

        if len(warehouses) <= 1:
            return super()._action_launch_stock_rule(
                previous_product_uom_qty=previous_product_uom_qty
            )

        return super(SaleOrderLine, self.with_context(
            multi_warehouse_separate_confirm=True
        ))._action_launch_stock_rule(
            previous_product_uom_qty=previous_product_uom_qty
        )


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def action_confirm(self):
        """
        Override to handle batch confirmation when multiple warehouses are involved.
        Confirm pickings one at a time to avoid singleton errors in other modules.
        """
        if self.env.context.get('multi_warehouse_separate_confirm') and len(self) > 1:
            for picking in self:
                super(StockPicking, picking).action_confirm()
            return True
        return super().action_confirm()

    def _get_partner_to_invoice(self):
        """Safety override in case of singleton issues"""
        self.ensure_one()
        return super()._get_partner_to_invoice()


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_new_picking_values(self):
        """
        Override to ensure the picking is created with the correct warehouse
        location when a line-level warehouse is set on the originating sale line.
        """
        vals = super()._get_new_picking_values()

        # Detect warehouse from procurement group / sale order line
        sale_line = self.sale_line_id
        if sale_line and sale_line.warehouse_id:
            wh = sale_line.warehouse_id
            # OUT picking: source = wh stock location, dest = customer
            if self.picking_type_id and self.picking_type_id.code == 'outgoing':
                vals['location_id'] = wh.lot_stock_id.id
                vals['picking_type_id'] = wh.out_type_id.id

        return vals

    def _assign_picking_post_confirm(self):
        """Ensure move location matches the picking after assignment."""
        res = super()._assign_picking_post_confirm() if hasattr(super(), '_assign_picking_post_confirm') else None

        sale_line = self.sale_line_id
        if sale_line and sale_line.warehouse_id:
            wh = sale_line.warehouse_id
            if self.picking_id and self.picking_id.picking_type_id.code == 'outgoing':
                if self.location_id != wh.lot_stock_id:
                    self.location_id = wh.lot_stock_id.id

        return res

    def _search_picking_for_assignation(self):
        """
        Override to prevent moves from different warehouses being merged
        into the same picking.
        """
        picking = super()._search_picking_for_assignation()

        sale_line = self.sale_line_id
        if sale_line and sale_line.warehouse_id and picking:
            # Verify the found picking belongs to the same warehouse
            picking_wh = picking.picking_type_id.warehouse_id
            if picking_wh and picking_wh != sale_line.warehouse_id:
                # Don't reuse this picking — force a new one
                return self.env['stock.picking']

        return picking


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _create_delivery_line(self, carrier, price_unit):
        """Override to ensure delivery line gets the order's warehouse"""
        result = super()._create_delivery_line(carrier, price_unit)
        if result and not result.warehouse_id:
            result.warehouse_id = self.warehouse_id
        return result












# from odoo import models, fields, api, _
# from collections import defaultdict
#
#
# class SaleOrderLine(models.Model):
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
#             # Get warehouses with stock
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
#             # If no stock found, use order's warehouse
#             if self.order_id and self.order_id.warehouse_id:
#                 self.warehouse_id = self.order_id.warehouse_id
#
#     def _prepare_procurement_values(self):
#         """Override to use line-specific warehouse"""
#         values = super(SaleOrderLine, self)._prepare_procurement_values()
#
#         # Use line's warehouse if set
#         if self.warehouse_id:
#             values['warehouse_id'] = self.warehouse_id
#
#         return values
#
#     def _action_launch_stock_rule(self, previous_product_uom_qty=False):
#         """
#         Override to ensure pickings are confirmed one at a time
#         """
#         # Store context flag to prevent recursive interception
#         if self.env.context.get('multi_warehouse_processing'):
#             return super(SaleOrderLine, self)._action_launch_stock_rule(
#                 previous_product_uom_qty=previous_product_uom_qty
#             )
#
#         # Check if we have multiple warehouses
#         warehouses = self.filtered(
#             lambda l: l.product_id.type in ['product', 'consu'] and l.warehouse_id
#         ).mapped('warehouse_id')
#
#         if len(warehouses) <= 1:
#             # Single warehouse - use standard flow
#             return super(SaleOrderLine, self)._action_launch_stock_rule(
#                 previous_product_uom_qty=previous_product_uom_qty
#             )
#
#         # Multiple warehouses - we need to intercept the picking confirmation
#         # Process lines with a special context that will catch the picking confirmation
#         return super(SaleOrderLine, self.with_context(
#             multi_warehouse_separate_confirm=True
#         ))._action_launch_stock_rule(
#             previous_product_uom_qty=previous_product_uom_qty
#         )
#
#
# class StockPicking(models.Model):
#     _inherit = 'stock.picking'
#
#     def action_confirm(self):
#         """
#         Override to handle batch confirmation when multiple warehouses are involved
#         Confirm pickings one at a time to avoid singleton errors in other modules
#         """
#         # Check if we're in multi-warehouse mode and have multiple pickings
#         if self.env.context.get('multi_warehouse_separate_confirm') and len(self) > 1:
#             # Confirm each picking individually
#             for picking in self:
#                 super(StockPicking, picking).action_confirm()
#             return True
#         else:
#             # Standard confirmation
#             return super(StockPicking, self).action_confirm()
#
#
# class SaleOrder(models.Model):
#     _inherit = 'sale.order'
#
#     def _create_delivery_line(self, carrier, price_unit):
#         """Override to prevent issues with delivery lines"""
#         result = super(SaleOrder, self)._create_delivery_line(carrier, price_unit)
#         # Ensure delivery line gets a warehouse
#         if result and not result.warehouse_id:
#             result.warehouse_id = self.warehouse_id
#         return result

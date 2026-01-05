from odoo import models, fields, api, _


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

            # Fallback to order's warehouse
            if self.order_id and self.order_id.warehouse_id:
                self.warehouse_id = self.order_id.warehouse_id

    def _prepare_procurement_values(self, group_id=False):
        """Override to use line-specific warehouse"""
        values = super()._prepare_procurement_values(group_id=group_id)

        if self.warehouse_id:
            values['warehouse_id'] = self.warehouse_id
            # Also update route to use warehouse's routes
            values['route_ids'] = self.warehouse_id.route_ids

        return values


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _create_delivery_line(self, carrier, price_unit):
        """Override to ensure delivery line gets a warehouse"""
        result = super()._create_delivery_line(carrier, price_unit)

        if result and not result.warehouse_id and self.warehouse_id:
            result.warehouse_id = self.warehouse_id

        return result

    def _action_confirm(self):
        """
        Override to handle multiple warehouses properly.
        This is safer than overriding action_confirm.
        """
        # Check if we have multiple warehouses
        warehouses = self.order_line.filtered(
            lambda l: l.product_id.type in ['product', 'consu'] and l.warehouse_id
        ).mapped('warehouse_id')

        if len(warehouses) > 1:
            # Process with multi-warehouse context
            return super(SaleOrder, self.with_context(
                multi_warehouse_mode=True
            ))._action_confirm()

        # Standard flow for single warehouse
        return super()._action_confirm()


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _get_stock_move_values(self, product_id, product_qty, product_uom,
                               location_dest_id, name, origin, company_id, values):
        """
        Override to respect line-specific warehouse in move values.
        This is safer than overriding picking creation.
        """
        move_values = super()._get_stock_move_values(
            product_id, product_qty, product_uom,
            location_dest_id, name, origin, company_id, values
        )

        # If we have a specific warehouse from sale line, use it
        if values.get('warehouse_id') and self.env.context.get('multi_warehouse_mode'):
            warehouse = values['warehouse_id']
            if isinstance(warehouse, int):
                warehouse = self.env['stock.warehouse'].browse(warehouse)

            # Update source location to warehouse's stock location
            move_values['location_id'] = warehouse.lot_stock_id.id
            move_values['warehouse_id'] = warehouse.id

        return move_values


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def action_confirm(self):
        """
        Safe override to handle batch confirmation in multi-warehouse scenarios.
        Confirms pickings individually to avoid singleton errors.
        """
        if self.env.context.get('multi_warehouse_mode') and len(self) > 1:
            # Confirm each picking individually to avoid singleton issues
            for picking in self:
                super(StockPicking, picking).action_confirm()
            return True

        return super().action_confirm()
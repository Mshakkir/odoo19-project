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

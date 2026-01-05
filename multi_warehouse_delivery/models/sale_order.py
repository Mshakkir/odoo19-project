from odoo import models, fields, api
from collections import defaultdict


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Delivery Warehouse',
        help='Warehouse from which this product will be delivered',
        domain="[('company_id', '=', company_id)]"
    )

    @api.onchange('product_id')
    def _onchange_product_id_set_warehouse(self):
        """Auto-select warehouse with available stock"""
        if self.product_id and self.product_id.type == 'product':
            # Get warehouses with stock
            warehouses = self.env['stock.warehouse'].search([
                ('company_id', '=', self.company_id.id)
            ])

            for warehouse in warehouses:
                stock = self.product_id.with_context(
                    warehouse=warehouse.id
                ).qty_available

                if stock > 0:
                    self.warehouse_id = warehouse.id
                    break

            # If no stock found, use order's warehouse
            if not self.warehouse_id:
                self.warehouse_id = self.order_id.warehouse_id


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        """Override to handle multiple warehouses"""
        result = super(SaleOrder, self).action_confirm()

        for order in self:
            # Group order lines by warehouse
            lines_by_warehouse = defaultdict(list)
            for line in order.order_line:
                if line.product_id.type in ['product', 'consu']:
                    warehouse = line.warehouse_id or order.warehouse_id
                    lines_by_warehouse[warehouse].append(line)

            # If multiple warehouses, split pickings
            if len(lines_by_warehouse) > 1:
                order._split_pickings_by_warehouse(lines_by_warehouse)

        return result

    def _split_pickings_by_warehouse(self, lines_by_warehouse):
        """Create separate picking for each warehouse"""
        self.ensure_one()

        # Cancel existing pickings if any
        existing_pickings = self.picking_ids.filtered(
            lambda p: p.state not in ['done', 'cancel']
        )
        if existing_pickings:
            existing_pickings.action_cancel()

        # Create new picking for each warehouse
        for warehouse, lines in lines_by_warehouse.items():
            picking_type = warehouse.out_type_id

            picking_vals = {
                'picking_type_id': picking_type.id,
                'partner_id': self.partner_shipping_id.id,
                'origin': self.name,
                'location_id': warehouse.lot_stock_id.id,
                'location_dest_id': self.partner_shipping_id.property_stock_customer.id,
                'sale_id': self.id,
                'company_id': self.company_id.id,
            }

            picking = self.env['stock.picking'].create(picking_vals)

            # Create moves for lines from this warehouse
            for line in lines:
                if line.product_id.type in ['product', 'consu'] and line.product_uom_qty > 0:
                    move_vals = {
                        'name': line.product_id.name,
                        'product_id': line.product_id.id,
                        'product_uom_qty': line.product_uom_qty,
                        'product_uom': line.product_uom.id,
                        'picking_id': picking.id,
                        'location_id': warehouse.lot_stock_id.id,
                        'location_dest_id': self.partner_shipping_id.property_stock_customer.id,
                        'sale_line_id': line.id,
                        'company_id': self.company_id.id,
                    }
                    self.env['stock.move'].create(move_vals)

            # Confirm the picking
            picking.action_confirm()
            picking.action_assign()

    def _prepare_picking_vals(self):
        """Override to use the first line's warehouse if different warehouses"""
        vals = super()._prepare_picking_vals()

        # Check if we have lines with different warehouses
        warehouses = self.order_line.mapped('warehouse_id')
        if len(warehouses) > 1:
            # This will be handled by _split_pickings_by_warehouse
            # Just return the default vals
            pass
        elif len(warehouses) == 1 and warehouses[0]:
            # All lines use the same custom warehouse
            vals['picking_type_id'] = warehouses[0].out_type_id.id
            vals['location_id'] = warehouses[0].lot_stock_id.id

        return vals
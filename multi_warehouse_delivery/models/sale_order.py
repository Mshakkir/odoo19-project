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


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        """Override to handle multiple warehouses"""
        # Call parent first
        result = super(SaleOrder, self).action_confirm()

        for order in self:
            # Only process if we have multiple warehouses
            warehouses_in_order = order.order_line.filtered(
                lambda l: l.product_id.type in ['product', 'consu']
            ).mapped('warehouse_id')

            if len(warehouses_in_order) > 1:
                # Group order lines by warehouse
                lines_by_warehouse = defaultdict(list)
                for line in order.order_line:
                    if line.product_id.type in ['product', 'consu']:
                        warehouse = line.warehouse_id or order.warehouse_id
                        lines_by_warehouse[warehouse].append(line)

                # Split pickings by warehouse
                order._split_pickings_by_warehouse(lines_by_warehouse)

        return result

    def _split_pickings_by_warehouse(self, lines_by_warehouse):
        """Create separate picking for each warehouse"""
        self.ensure_one()

        # Get existing pickings that are not done or cancelled
        existing_pickings = self.picking_ids.filtered(
            lambda p: p.state not in ['done', 'cancel']
        )

        # Cancel and unlink existing pickings
        if existing_pickings:
            for picking in existing_pickings:
                # Cancel moves first
                picking.move_ids.filtered(lambda m: m.state not in ['done', 'cancel'])._action_cancel()
                picking.action_cancel()

        # Create new picking for each warehouse
        for warehouse, lines in lines_by_warehouse.items():
            if not warehouse:
                continue

            picking_type = warehouse.out_type_id

            # Prepare picking values
            picking_vals = {
                'picking_type_id': picking_type.id,
                'partner_id': self.partner_shipping_id.id,
                'origin': self.name,
                'location_id': warehouse.lot_stock_id.id,
                'location_dest_id': self.partner_shipping_id.property_stock_customer.id or self.env.ref(
                    'stock.stock_location_customers').id,
                'company_id': self.company_id.id,
            }

            # Create picking
            picking = self.env['stock.picking'].create(picking_vals)

            # Create stock moves for each line from this warehouse
            for line in lines:
                if line.product_id.type in ['product', 'consu'] and line.product_uom_qty > 0:
                    move_vals = line._prepare_procurement_values()
                    move_vals.update({
                        'name': line.name or line.product_id.name,
                        'product_id': line.product_id.id,
                        'product_uom_qty': line.product_uom_qty,
                        'product_uom': line.product_uom.id,
                        'picking_id': picking.id,
                        'location_id': warehouse.lot_stock_id.id,
                        'location_dest_id': self.partner_shipping_id.property_stock_customer.id or self.env.ref(
                            'stock.stock_location_customers').id,
                        'sale_line_id': line.id,
                        'company_id': self.company_id.id,
                        'origin': self.name,
                        'picking_type_id': picking_type.id,
                    })

                    # Create the move
                    move = self.env['stock.move'].create(move_vals)

            # Confirm and assign picking
            if picking.move_ids:
                picking.action_confirm()
                picking.action_assign()
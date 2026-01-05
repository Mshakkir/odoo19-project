from odoo import models, fields, api, _
from collections import defaultdict


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Destination Warehouse',
        help='Warehouse where this product will be received',
        domain="[('company_id', '=', company_id)]",
        copy=False
    )

    @api.onchange('product_id')
    def _onchange_product_id_set_warehouse(self):
        """Auto-select warehouse with lowest stock"""
        if self.product_id and self.product_id.type == 'product':
            warehouses = self.env['stock.warehouse'].search([
                ('company_id', '=', self.company_id.id or self.env.company.id)
            ])

            min_stock = float('inf')
            selected_warehouse = None

            for warehouse in warehouses:
                stock = self.product_id.with_context(
                    warehouse=warehouse.id
                ).qty_available

                if stock < min_stock:
                    min_stock = stock
                    selected_warehouse = warehouse

            if selected_warehouse:
                self.warehouse_id = selected_warehouse.id
            elif self.order_id and self.order_id.picking_type_id:
                self.warehouse_id = self.order_id.picking_type_id.warehouse_id.id


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def _create_picking(self):
        """Override to create separate pickings for each warehouse"""
        # Group lines by warehouse first
        warehouses_in_order = self.order_line.filtered(
            lambda l: l.product_id.type in ['product', 'consu'] and l.warehouse_id
        ).mapped('warehouse_id')

        # If single or no warehouse, use standard flow
        if len(warehouses_in_order) <= 1:
            return super()._create_picking()

        # Multi-warehouse handling
        StockPicking = self.env['stock.picking']
        res = self.env['stock.picking']

        for order in self:
            # Group lines by warehouse
            lines_by_warehouse = defaultdict(lambda: self.env['purchase.order.line'])

            for line in order.order_line.filtered(
                    lambda l: l.product_id.type in ['product', 'consu']
            ):
                warehouse = line.warehouse_id or order.picking_type_id.warehouse_id
                lines_by_warehouse[warehouse] |= line

            # Create picking for each warehouse
            for warehouse, lines in lines_by_warehouse.items():
                # Get appropriate picking type for warehouse
                picking_type = warehouse.in_type_id

                # Check for existing picking
                existing_picking = order.picking_ids.filtered(
                    lambda p: (
                            p.picking_type_id.warehouse_id == warehouse
                            and p.state not in ['done', 'cancel']
                    )
                )

                if existing_picking:
                    picking = existing_picking[0]
                else:
                    # Create new picking
                    picking = StockPicking.create(
                        order._prepare_picking_vals(picking_type, warehouse)
                    )

                # Let Odoo's standard flow create moves, but update destination
                for line in lines:
                    # Use standard move creation
                    moves = line._create_stock_moves(picking)

                    # Update destination location to warehouse's input location
                    moves.write({
                        'location_dest_id': warehouse.lot_stock_id.id,
                        'warehouse_id': warehouse.id,
                    })

                    # Confirm moves
                    moves._action_confirm()
                    moves._action_assign()

                res |= picking

        return res

    def _prepare_picking_vals(self, picking_type, warehouse):
        """Prepare picking values for a specific warehouse"""
        self.ensure_one()
        return {
            'picking_type_id': picking_type.id,
            'partner_id': self.partner_id.id,
            'date': self.date_order,
            'origin': self.name,
            'location_dest_id': warehouse.lot_stock_id.id,
            'location_id': (
                    self.partner_id.property_stock_supplier.id
                    or self.env.ref('stock.stock_location_suppliers').id
            ),
            'company_id': self.company_id.id,
        }

    def _get_destination_location(self):
        """Override to use line-specific warehouse location"""
        self.ensure_one()
        warehouses = self.order_line.mapped('warehouse_id')

        if len(warehouses) == 1:
            return warehouses.lot_stock_id.id

        # Multiple warehouses - will be handled in _create_picking
        return super()._get_destination_location()
# from odoo import models, fields, api, _
# from collections import defaultdict
#
#
# class PurchaseOrderLine(models.Model):
#     _inherit = 'purchase.order.line'
#
#     warehouse_id = fields.Many2one(
#         'stock.warehouse',
#         string='Destination Warehouse',
#         help='Warehouse where this product will be received',
#         domain="[('company_id', '=', company_id)]",
#         copy=False
#     )
#
#     @api.onchange('product_id')
#     def _onchange_product_id_set_warehouse(self):
#         """Auto-select warehouse with lowest stock"""
#         if self.product_id and self.product_id.type == 'product':
#             # Get warehouses
#             warehouses = self.env['stock.warehouse'].search([
#                 ('company_id', '=', self.company_id.id or self.env.company.id)
#             ])
#
#             # Find warehouse with lowest stock
#             min_stock = float('inf')
#             selected_warehouse = None
#
#             for warehouse in warehouses:
#                 stock = self.product_id.with_context(
#                     warehouse=warehouse.id
#                 ).qty_available
#
#                 if stock < min_stock:
#                     min_stock = stock
#                     selected_warehouse = warehouse
#
#             if selected_warehouse:
#                 self.warehouse_id = selected_warehouse.id
#             elif self.order_id and self.order_id.picking_type_id:
#                 # Use order's warehouse
#                 self.warehouse_id = self.order_id.picking_type_id.warehouse_id.id
#
#     def _prepare_stock_moves(self, picking):
#         """Override to use line-specific warehouse"""
#         values = super(PurchaseOrderLine, self)._prepare_stock_moves(picking)
#
#         # Update destination location to use line's warehouse if set
#         if self.warehouse_id and values:
#             for move_vals in values:
#                 # Update the destination location to the warehouse's input location
#                 move_vals['location_dest_id'] = self.warehouse_id.lot_stock_id.id
#                 move_vals['warehouse_id'] = self.warehouse_id.id
#
#         return values
#
#
# class PurchaseOrder(models.Model):
#     _inherit = 'purchase.order'
#
#     def button_confirm(self):
#         """Override to handle multiple warehouses"""
#         # Check if we have multiple warehouses before confirmation
#         for order in self:
#             warehouses_in_order = order.order_line.filtered(
#                 lambda l: l.product_id.type in ['product', 'consu'] and l.warehouse_id
#             ).mapped('warehouse_id')
#
#             if len(warehouses_in_order) > 1:
#                 # Set context flag for multi-warehouse handling
#                 return super(PurchaseOrder, self.with_context(
#                     multi_warehouse_separate_confirm=True
#                 )).button_confirm()
#
#         # Standard confirmation for single warehouse
#         return super(PurchaseOrder, self).button_confirm()
#
#     def _create_picking(self):
#         """Override to create separate pickings for each warehouse"""
#         # Check if we have multiple warehouses
#         warehouses_in_order = self.order_line.filtered(
#             lambda l: l.product_id.type in ['product', 'consu'] and l.warehouse_id
#         ).mapped('warehouse_id')
#
#         if len(warehouses_in_order) <= 1:
#             # Single warehouse - use standard flow
#             return super(PurchaseOrder, self)._create_picking()
#
#         # Multiple warehouses - create separate picking for each
#         StockPicking = self.env['stock.picking']
#
#         for order in self:
#             if any(product.type in ['product', 'consu'] for product in order.order_line.mapped('product_id')):
#                 # Group lines by warehouse
#                 lines_by_warehouse = defaultdict(list)
#                 for line in order.order_line:
#                     if line.product_id.type in ['product', 'consu']:
#                         warehouse = line.warehouse_id or order.picking_type_id.warehouse_id
#                         lines_by_warehouse[warehouse].append(line)
#
#                 # Create picking for each warehouse
#                 for warehouse, lines in lines_by_warehouse.items():
#                     if not lines:
#                         continue
#
#                     # Get or create picking type for this warehouse
#                     picking_type = warehouse.in_type_id
#
#                     # Check if a picking already exists for this warehouse
#                     existing_picking = order.picking_ids.filtered(
#                         lambda p: p.picking_type_id.warehouse_id == warehouse and p.state not in ['done', 'cancel']
#                     )
#
#                     if existing_picking:
#                         picking = existing_picking[0]
#                     else:
#                         # Create new picking
#                         picking_vals = {
#                             'picking_type_id': picking_type.id,
#                             'partner_id': order.partner_id.id,
#                             'date': order.date_order,
#                             'origin': order.name,
#                             'location_dest_id': warehouse.lot_stock_id.id,
#                             'location_id': order.partner_id.property_stock_supplier.id or self.env.ref(
#                                 'stock.stock_location_suppliers').id,
#                             'company_id': order.company_id.id,
#                         }
#                         picking = StockPicking.create(picking_vals)
#
#                     # Create moves for lines in this warehouse
#                     for line in lines:
#                         moves = line._create_stock_moves(picking)
#                         moves._action_confirm()
#                         moves._action_assign()
#
#         return True
#
#     def _get_destination_location(self):
#         """Override to use line-specific warehouse location"""
#         self.ensure_one()
#         # This method is used by the standard flow
#         # If we have multiple warehouses, we'll handle it in _create_picking
#         warehouses = self.order_line.mapped('warehouse_id')
#         if len(warehouses) == 1:
#             return warehouses.lot_stock_id.id
#         return super(PurchaseOrder, self)._get_destination_location()
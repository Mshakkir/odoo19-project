# from odoo import models, fields, api, _
# from collections import defaultdict
#
#
# class AccountMoveLine(models.Model):
#     _inherit = 'account.move.line'
#
#     warehouse_id = fields.Many2one(
#         'stock.warehouse',
#         string='Delivery Warehouse',
#         help='Warehouse from which this product will be delivered/received',
#         domain="[('company_id', '=', company_id)]",
#         copy=True
#     )
#
#     @api.onchange('product_id')
#     def _onchange_product_id_set_warehouse(self):
#         """Auto-select warehouse with available stock for customer invoices"""
#         if self.product_id and self.product_id.type == 'product' and self.move_id.move_type in ['out_invoice',
#                                                                                                 'out_refund']:
#             # Get warehouses with stock for customer invoices
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
#             # If no stock found, use company's main warehouse
#             if not self.warehouse_id and warehouses:
#                 self.warehouse_id = warehouses[0]
#
#         elif self.product_id and self.product_id.type == 'product' and self.move_id.move_type in ['in_invoice',
#                                                                                                   'in_refund']:
#             # For vendor bills, default to company's main warehouse
#             warehouses = self.env['stock.warehouse'].search([
#                 ('company_id', '=', self.company_id.id or self.env.company.id)
#             ], limit=1)
#             if warehouses:
#                 self.warehouse_id = warehouses[0]
#
#
# class AccountMove(models.Model):
#     _inherit = 'account.move'
#
#     def action_post(self):
#         """Override to create deliveries/receipts when invoice is posted"""
#         result = super(AccountMove, self).action_post()
#
#         for move in self:
#             # Only process customer invoices and vendor bills with products
#             if move.move_type in ['out_invoice',
#                                   'in_invoice'] and not move.sale_order_ids and not move.purchase_order_id:
#                 # Check if we have different warehouses for different lines
#                 product_lines = move.invoice_line_ids.filtered(
#                     lambda l: l.product_id and l.product_id.type in ['product', 'consu'] and l.quantity > 0
#                 )
#
#                 if product_lines:
#                     warehouses_in_invoice = product_lines.mapped('warehouse_id')
#
#                     if len(warehouses_in_invoice) >= 1:
#                         # Group invoice lines by warehouse
#                         lines_by_warehouse = defaultdict(list)
#                         for line in product_lines:
#                             warehouse = line.warehouse_id or warehouses_in_invoice[0]
#                             lines_by_warehouse[warehouse].append(line)
#
#                         # Create pickings for each warehouse
#                         if move.move_type == 'out_invoice':
#                             move._create_delivery_pickings(lines_by_warehouse)
#                         elif move.move_type == 'in_invoice':
#                             move._create_receipt_pickings(lines_by_warehouse)
#
#         return result
#
#     def _create_delivery_pickings(self, lines_by_warehouse):
#         """Create delivery pickings for customer invoices"""
#         self.ensure_one()
#
#         for warehouse, lines in lines_by_warehouse.items():
#             if not warehouse:
#                 continue
#
#             picking_type = warehouse.out_type_id
#
#             picking_vals = {
#                 'picking_type_id': picking_type.id,
#                 'partner_id': self.partner_id.id,
#                 'origin': self.name,
#                 'location_id': warehouse.lot_stock_id.id,
#                 'location_dest_id': self.partner_id.property_stock_customer.id or self.env.ref(
#                     'stock.stock_location_customers').id,
#                 'company_id': self.company_id.id,
#                 'move_type': 'direct',
#             }
#
#             picking = self.env['stock.picking'].create(picking_vals)
#
#             # Create stock moves
#             for line in lines:
#                 if line.product_id.type in ['product', 'consu'] and line.quantity > 0:
#                     move_vals = {
#                         'name': line.product_id.name,
#                         'product_id': line.product_id.id,
#                         'product_uom_qty': line.quantity,
#                         'product_uom': line.product_uom_id.id,
#                         'picking_id': picking.id,
#                         'location_id': warehouse.lot_stock_id.id,
#                         'location_dest_id': self.partner_id.property_stock_customer.id or self.env.ref(
#                             'stock.stock_location_customers').id,
#                         'company_id': self.company_id.id,
#                         'origin': self.name,
#                         'picking_type_id': picking_type.id,
#                     }
#
#                     self.env['stock.move'].create(move_vals)
#
#             if picking.move_ids:
#                 picking.action_confirm()
#                 picking.action_assign()
#
#     def _create_receipt_pickings(self, lines_by_warehouse):
#         """Create receipt pickings for vendor bills"""
#         self.ensure_one()
#
#         for warehouse, lines in lines_by_warehouse.items():
#             if not warehouse:
#                 continue
#
#             picking_type = warehouse.in_type_id
#
#             picking_vals = {
#                 'picking_type_id': picking_type.id,
#                 'partner_id': self.partner_id.id,
#                 'origin': self.name,
#                 'location_id': self.partner_id.property_stock_supplier.id or self.env.ref(
#                     'stock.stock_location_suppliers').id,
#                 'location_dest_id': warehouse.lot_stock_id.id,
#                 'company_id': self.company_id.id,
#                 'move_type': 'direct',
#             }
#
#             picking = self.env['stock.picking'].create(picking_vals)
#
#             # Create stock moves
#             for line in lines:
#                 if line.product_id.type in ['product', 'consu'] and line.quantity > 0:
#                     move_vals = {
#                         'name': line.product_id.name,
#                         'product_id': line.product_id.id,
#                         'product_uom_qty': line.quantity,
#                         'product_uom': line.product_uom_id.id,
#                         'picking_id': picking.id,
#                         'location_id': self.partner_id.property_stock_supplier.id or self.env.ref(
#                             'stock.stock_location_suppliers').id,
#                         'location_dest_id': warehouse.lot_stock_id.id,
#                         'company_id': self.company_id.id,
#                         'origin': self.name,
#                         'picking_type_id': picking_type.id,
#                     }
#
#                     self.env['stock.move'].create(move_vals)
#
#             if picking.move_ids:
#                 picking.action_confirm()
#                 picking.action_assign()


# from odoo import models, fields, api, _
# from collections import defaultdict
#
#
# class AccountMoveLine(models.Model):
#     _inherit = 'account.move.line'
#
#     warehouse_id = fields.Many2one(
#         'stock.warehouse',
#         string='Delivery Warehouse',
#         help='Warehouse from which this product will be delivered/received',
#         domain="[('company_id', '=', company_id)]",
#         copy=True
#     )
#
#     @api.onchange('product_id')
#     def _onchange_product_id_set_warehouse(self):
#         """Auto-select warehouse with available stock for customer invoices"""
#         if self.product_id and self.product_id.type == 'product' and self.move_id.move_type in ['out_invoice',
#                                                                                                 'out_refund']:
#             # Get warehouses with stock for customer invoices
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
#             # If no stock found, use company's main warehouse
#             if not self.warehouse_id and warehouses:
#                 self.warehouse_id = warehouses[0]
#
#         elif self.product_id and self.product_id.type == 'product' and self.move_id.move_type in ['in_invoice',
#                                                                                                   'in_refund']:
#             # For vendor bills, default to company's main warehouse
#             warehouses = self.env['stock.warehouse'].search([
#                 ('company_id', '=', self.company_id.id or self.env.company.id)
#             ], limit=1)
#             if warehouses:
#                 self.warehouse_id = warehouses[0]
#
#
# class AccountMove(models.Model):
#     _inherit = 'account.move'
#
#     def action_post(self):
#         """Override to create deliveries/receipts when invoice is posted"""
#         result = super(AccountMove, self).action_post()
#
#         for move in self:
#             # Only process customer invoices and vendor bills with products
#             # Check if invoice is linked to sale/purchase orders
#             has_sale_order = any(line.sale_line_ids for line in move.invoice_line_ids)
#             has_purchase_order = any(line.purchase_line_id for line in move.invoice_line_ids)
#
#             if move.move_type in ['out_invoice', 'in_invoice'] and not has_sale_order and not has_purchase_order:
#                 # Check if we have different warehouses for different lines
#                 product_lines = move.invoice_line_ids.filtered(
#                     lambda l: l.product_id and l.product_id.type in ['product', 'consu'] and l.quantity > 0
#                 )
#
#                 if product_lines:
#                     warehouses_in_invoice = product_lines.mapped('warehouse_id')
#
#                     if len(warehouses_in_invoice) >= 1:
#                         # Group invoice lines by warehouse
#                         lines_by_warehouse = defaultdict(list)
#                         for line in product_lines:
#                             warehouse = line.warehouse_id or warehouses_in_invoice[0]
#                             lines_by_warehouse[warehouse].append(line)
#
#                         # Create pickings for each warehouse
#                         if move.move_type == 'out_invoice':
#                             move._create_delivery_pickings(lines_by_warehouse)
#                         elif move.move_type == 'in_invoice':
#                             move._create_receipt_pickings(lines_by_warehouse)
#
#         return result
#
#     def _create_delivery_pickings(self, lines_by_warehouse):
#         """Create delivery pickings for customer invoices"""
#         self.ensure_one()
#
#         for warehouse, lines in lines_by_warehouse.items():
#             if not warehouse:
#                 continue
#
#             picking_type = warehouse.out_type_id
#
#             picking_vals = {
#                 'picking_type_id': picking_type.id,
#                 'partner_id': self.partner_id.id,
#                 'origin': self.name,
#                 'location_id': warehouse.lot_stock_id.id,
#                 'location_dest_id': self.partner_id.property_stock_customer.id or self.env.ref(
#                     'stock.stock_location_customers').id,
#                 'company_id': self.company_id.id,
#                 'move_type': 'direct',
#             }
#
#             picking = self.env['stock.picking'].create(picking_vals)
#
#             # Create stock moves
#             for line in lines:
#                 if line.product_id.type in ['product', 'consu'] and line.quantity > 0:
#                     move_vals = {
#                         'product_id': line.product_id.id,
#                         'product_uom_qty': line.quantity,
#                         'product_uom': line.product_uom_id.id,
#                         'picking_id': picking.id,
#                         'location_id': warehouse.lot_stock_id.id,
#                         'location_dest_id': self.partner_id.property_stock_customer.id or self.env.ref(
#                             'stock.stock_location_customers').id,
#                         'company_id': self.company_id.id,
#                         'origin': self.name,
#                         'picking_type_id': picking_type.id,
#                     }
#
#                     self.env['stock.move'].create(move_vals)
#
#             if picking.move_ids:
#                 picking.action_confirm()
#                 picking.action_assign()
#
#     def _create_receipt_pickings(self, lines_by_warehouse):
#         """Create receipt pickings for vendor bills"""
#         self.ensure_one()
#
#         for warehouse, lines in lines_by_warehouse.items():
#             if not warehouse:
#                 continue
#
#             picking_type = warehouse.in_type_id
#
#             picking_vals = {
#                 'picking_type_id': picking_type.id,
#                 'partner_id': self.partner_id.id,
#                 'origin': self.name,
#                 'location_id': self.partner_id.property_stock_supplier.id or self.env.ref(
#                     'stock.stock_location_suppliers').id,
#                 'location_dest_id': warehouse.lot_stock_id.id,
#                 'company_id': self.company_id.id,
#                 'move_type': 'direct',
#             }
#
#             picking = self.env['stock.picking'].create(picking_vals)
#
#             # Create stock moves
#             for line in lines:
#                 if line.product_id.type in ['product', 'consu'] and line.quantity > 0:
#                     move_vals = {
#                         'product_id': line.product_id.id,
#                         'product_uom_qty': line.quantity,
#                         'product_uom': line.product_uom_id.id,
#                         'picking_id': picking.id,
#                         'location_id': self.partner_id.property_stock_supplier.id or self.env.ref(
#                             'stock.stock_location_suppliers').id,
#                         'location_dest_id': warehouse.lot_stock_id.id,
#                         'company_id': self.company_id.id,
#                         'origin': self.name,
#                         'picking_type_id': picking_type.id,
#                     }
#
#                     self.env['stock.move'].create(move_vals)
#
#             if picking.move_ids:
#                 picking.action_confirm()
#                 picking.action_assign()

from odoo import models, fields, api, _
from collections import defaultdict


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Delivery Warehouse',
        help='Warehouse from which this product will be delivered/received',
        domain="[('company_id', '=', company_id)]",
        copy=True
    )

    @api.onchange('product_id')
    def _onchange_product_id_set_warehouse(self):
        """Auto-select warehouse with available stock for customer invoices"""
        if self.product_id and self.product_id.type == 'product' and self.move_id.move_type in ['out_invoice',
                                                                                                'out_refund']:
            # Get warehouses with stock for customer invoices
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

            # If no stock found, use company's main warehouse
            if not self.warehouse_id and warehouses:
                self.warehouse_id = warehouses[0]

        elif self.product_id and self.product_id.type == 'product' and self.move_id.move_type in ['in_invoice',
                                                                                                  'in_refund']:
            # For vendor bills, default to company's main warehouse
            warehouses = self.env['stock.warehouse'].search([
                ('company_id', '=', self.company_id.id or self.env.company.id)
            ], limit=1)
            if warehouses:
                self.warehouse_id = warehouses[0]


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        """Override to create deliveries/receipts when invoice is posted"""
        result = super(AccountMove, self).action_post()

        for move in self:
            # Only process customer invoices and vendor bills with products
            # Check if invoice is linked to sale/purchase orders
            has_sale_order = any(line.sale_line_ids for line in move.invoice_line_ids)
            has_purchase_order = any(line.purchase_line_id for line in move.invoice_line_ids)

            if move.move_type in ['out_invoice', 'in_invoice'] and not has_sale_order and not has_purchase_order:
                # Check if we have different warehouses for different lines
                product_lines = move.invoice_line_ids.filtered(
                    lambda l: l.product_id and l.product_id.type in ['product', 'consu'] and l.quantity > 0
                )

                if product_lines:
                    warehouses_in_invoice = product_lines.mapped('warehouse_id')

                    if len(warehouses_in_invoice) >= 1:
                        # Group invoice lines by warehouse
                        lines_by_warehouse = defaultdict(list)
                        for line in product_lines:
                            warehouse = line.warehouse_id or warehouses_in_invoice[0]
                            lines_by_warehouse[warehouse].append(line)

                        # Create pickings for each warehouse
                        if move.move_type == 'out_invoice':
                            move._create_delivery_pickings(lines_by_warehouse)
                        elif move.move_type == 'in_invoice':
                            move._create_receipt_pickings(lines_by_warehouse)

        return result

    def _create_delivery_pickings(self, lines_by_warehouse):
        """Create delivery pickings for customer invoices"""
        self.ensure_one()

        # Determine source warehouse (the warehouse creating the invoice)
        # This could be based on user's default warehouse or company's main warehouse
        source_warehouse = None
        company_warehouses = self.env['stock.warehouse'].search([
            ('company_id', '=', self.company_id.id)
        ], limit=1)
        if company_warehouses:
            source_warehouse = company_warehouses[0]

        for warehouse, lines in lines_by_warehouse.items():
            if not warehouse:
                continue

            picking_type = warehouse.out_type_id

            picking_vals = {
                'picking_type_id': picking_type.id,
                'partner_id': self.partner_id.id,
                'origin': self.name,
                'location_id': warehouse.lot_stock_id.id,
                'location_dest_id': self.partner_id.property_stock_customer.id or self.env.ref(
                    'stock.stock_location_customers').id,
                'company_id': self.company_id.id,
                'move_type': 'direct',
                'source_warehouse_id': source_warehouse.id if source_warehouse and source_warehouse != warehouse else False,
            }

            picking = self.env['stock.picking'].create(picking_vals)

            # Create stock moves
            for line in lines:
                if line.product_id.type in ['product', 'consu'] and line.quantity > 0:
                    move_vals = {
                        'product_id': line.product_id.id,
                        'product_uom_qty': line.quantity,
                        'product_uom': line.product_uom_id.id,
                        'picking_id': picking.id,
                        'location_id': warehouse.lot_stock_id.id,
                        'location_dest_id': self.partner_id.property_stock_customer.id or self.env.ref(
                            'stock.stock_location_customers').id,
                        'company_id': self.company_id.id,
                        'origin': self.name,
                        'picking_type_id': picking_type.id,
                        'source_warehouse_id': source_warehouse.id if source_warehouse and source_warehouse != warehouse else False,
                    }

                    self.env['stock.move'].create(move_vals)

            if picking.move_ids:
                picking.action_confirm()
                picking.action_assign()

    def _create_receipt_pickings(self, lines_by_warehouse):
        """Create receipt pickings for vendor bills"""
        self.ensure_one()

        # Determine source warehouse
        source_warehouse = None
        company_warehouses = self.env['stock.warehouse'].search([
            ('company_id', '=', self.company_id.id)
        ], limit=1)
        if company_warehouses:
            source_warehouse = company_warehouses[0]

        for warehouse, lines in lines_by_warehouse.items():
            if not warehouse:
                continue

            picking_type = warehouse.in_type_id

            picking_vals = {
                'picking_type_id': picking_type.id,
                'partner_id': self.partner_id.id,
                'origin': self.name,
                'location_id': self.partner_id.property_stock_supplier.id or self.env.ref(
                    'stock.stock_location_suppliers').id,
                'location_dest_id': warehouse.lot_stock_id.id,
                'company_id': self.company_id.id,
                'move_type': 'direct',
                'source_warehouse_id': source_warehouse.id if source_warehouse and source_warehouse != warehouse else False,
            }

            picking = self.env['stock.picking'].create(picking_vals)

            # Create stock moves
            for line in lines:
                if line.product_id.type in ['product', 'consu'] and line.quantity > 0:
                    move_vals = {
                        'product_id': line.product_id.id,
                        'product_uom_qty': line.quantity,
                        'product_uom': line.product_uom_id.id,
                        'picking_id': picking.id,
                        'location_id': self.partner_id.property_stock_supplier.id or self.env.ref(
                            'stock.stock_location_suppliers').id,
                        'location_dest_id': warehouse.lot_stock_id.id,
                        'company_id': self.company_id.id,
                        'origin': self.name,
                        'picking_type_id': picking_type.id,
                        'source_warehouse_id': source_warehouse.id if source_warehouse and source_warehouse != warehouse else False,
                    }

                    self.env['stock.move'].create(move_vals)

            if picking.move_ids:
                picking.action_confirm()
                picking.action_assign()
from odoo import models, fields, api, _


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        help='Warehouse for this product line',
        domain="[('company_id', '=', company_id)]",
        copy=False
    )

    @api.onchange('product_id')
    def _onchange_product_id_set_warehouse(self):
        """Auto-select warehouse with available stock for product lines"""
        if self.product_id and self.product_id.type == 'product' and self.move_id.move_type in ['out_invoice',
                                                                                                'out_refund']:
            # Get warehouses with stock
            warehouses = self.env['stock.warehouse'].search([
                ('company_id', '=', self.company_id.id or self.env.company.id)
            ])

            # Find warehouse with highest stock for customer invoices
            max_stock = 0
            selected_warehouse = None

            for warehouse in warehouses:
                stock = self.product_id.with_context(
                    warehouse=warehouse.id
                ).qty_available

                if stock > max_stock:
                    max_stock = stock
                    selected_warehouse = warehouse

            if selected_warehouse:
                self.warehouse_id = selected_warehouse.id
            elif self.move_id and self.move_id.company_id:
                # Use default warehouse
                default_warehouse = self.env['stock.warehouse'].search([
                    ('company_id', '=', self.move_id.company_id.id)
                ], limit=1)
                if default_warehouse:
                    self.warehouse_id = default_warehouse.id

        elif self.product_id and self.product_id.type == 'product' and self.move_id.move_type in ['in_invoice',
                                                                                                  'in_refund']:
            # For vendor bills, select warehouse with lowest stock
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


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _stock_account_prepare_anglo_saxon_out_lines_vals(self):
        """Override to consider warehouse from invoice lines"""
        lines_vals_list = super()._stock_account_prepare_anglo_saxon_out_lines_vals()

        # Update lines with warehouse information if needed
        for vals in lines_vals_list:
            # Get the related invoice line
            invoice_line = self.env['account.move.line'].browse(vals.get('move_id'))
            if invoice_line and invoice_line.warehouse_id:
                vals['warehouse_id'] = invoice_line.warehouse_id.id

        return lines_vals_list

    def _create_picking_from_invoice(self):
        """
        Create stock picking when invoice is validated (for direct invoices)
        This handles invoices created without sales orders
        """
        for move in self:
            # Only process customer invoices and vendor bills
            if move.move_type not in ['out_invoice', 'in_invoice', 'out_refund', 'in_refund']:
                continue

            # Skip if already linked to a picking or purchase/sale order
            if move.invoice_line_ids.mapped('sale_line_ids') or move.invoice_line_ids.mapped('purchase_line_id'):
                continue

            # Check if we have stockable products
            stockable_lines = move.invoice_line_ids.filtered(
                lambda l: l.product_id and l.product_id.type == 'product' and l.quantity != 0
            )

            if not stockable_lines:
                continue

            # Group lines by warehouse
            from collections import defaultdict
            lines_by_warehouse = defaultdict(list)

            for line in stockable_lines:
                warehouse = line.warehouse_id
                if not warehouse:
                    # Get default warehouse
                    warehouse = self.env['stock.warehouse'].search([
                        ('company_id', '=', move.company_id.id)
                    ], limit=1)

                if warehouse:
                    lines_by_warehouse[warehouse].append(line)

            # Create picking for each warehouse
            for warehouse, lines in lines_by_warehouse.items():
                self._create_picking_for_warehouse(move, warehouse, lines)

    def _create_picking_for_warehouse(self, invoice, warehouse, lines):
        """Create a picking for specific warehouse and invoice lines"""
        StockPicking = self.env['stock.picking']

        # Determine picking type based on invoice type
        if invoice.move_type in ['out_invoice', 'out_refund']:
            picking_type = warehouse.out_type_id
            location_id = warehouse.lot_stock_id.id
            location_dest_id = self.env.ref('stock.stock_location_customers').id
        else:  # in_invoice, in_refund
            picking_type = warehouse.in_type_id
            location_id = self.env.ref('stock.stock_location_suppliers').id
            location_dest_id = warehouse.lot_stock_id.id

        # Prepare picking values
        picking_vals = {
            'picking_type_id': picking_type.id,
            'partner_id': invoice.partner_id.id,
            'origin': invoice.name,
            'location_id': location_id,
            'location_dest_id': location_dest_id,
            'company_id': invoice.company_id.id,
            'move_type': 'direct',
        }

        picking = StockPicking.create(picking_vals)

        # Create stock moves for each line
        for line in lines:
            if not line.product_id or line.product_id.type != 'product':
                continue

            # Adjust quantity based on refund
            quantity = line.quantity
            if invoice.move_type in ['out_refund', 'in_refund']:
                quantity = -quantity

            move_vals = {
                'name': line.product_id.name,
                'product_id': line.product_id.id,
                'product_uom_qty': abs(quantity),
                'product_uom': line.product_uom_id.id,
                'picking_id': picking.id,
                'location_id': location_id,
                'location_dest_id': location_dest_id,
                'company_id': invoice.company_id.id,
                'picking_type_id': picking_type.id,
                'origin': invoice.name,
                'warehouse_id': warehouse.id,
            }

            self.env['stock.move'].create(move_vals)

        # Confirm the picking
        if picking.move_ids:
            picking.action_confirm()
            # Optionally auto-assign
            picking.action_assign()

        return picking

    def action_post(self):
        """Override to create pickings for direct invoices"""
        res = super().action_post()

        # Create pickings for invoices without sales/purchase orders
        for move in self:
            if move.state == 'posted':
                # Check if this is a direct invoice (no SO/PO)
                has_so = any(line.sale_line_ids for line in move.invoice_line_ids)
                has_po = any(line.purchase_line_id for line in move.invoice_line_ids)

                if not has_so and not has_po:
                    try:
                        move._create_picking_from_invoice()
                    except Exception as e:
                        # Log error but don't block invoice posting
                        import logging
                        _logger = logging.getLogger(__name__)
                        _logger.warning(f"Could not create picking from invoice {move.name}: {str(e)}")

        return res
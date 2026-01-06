#
# from odoo import models, fields, api, _
# from odoo.exceptions import UserError
# import logging
#
# _logger = logging.getLogger(__name__)
#
#
# class AccountMove(models.Model):
#     _inherit = 'account.move'
#
#     picking_id = fields.Many2one('stock.picking', string='Delivery Order', readonly=True, copy=False)
#     create_delivery = fields.Boolean(
#         string='Create Delivery Order',
#         default=False,
#         help='Check this to automatically create delivery order on invoice validation'
#     )
#     warehouse_id = fields.Many2one(
#         'stock.warehouse',
#         string='Warehouse',
#         help='Select warehouse for stock reduction. If not set, default warehouse will be used.'
#     )
#
#     @api.onchange('invoice_line_ids')
#     def _onchange_invoice_lines_set_warehouse(self):
#         """Auto-set warehouse based on analytic account from invoice lines"""
#         # ONLY for customer invoices/credit notes
#         if self.move_type not in ['out_invoice', 'out_refund']:
#             return
#
#         if self.invoice_line_ids and not self.warehouse_id:
#             for line in self.invoice_line_ids:
#                 if line.analytic_distribution:
#                     analytic_dict = line.analytic_distribution
#                     if analytic_dict:
#                         try:
#                             analytic_id = int(list(analytic_dict.keys())[0])
#                             analytic_account = self.env['account.analytic.account'].browse(analytic_id)
#                             if analytic_account:
#                                 warehouse = self.env['stock.warehouse'].search([
#                                     ('name', 'ilike', analytic_account.name),
#                                     ('company_id', '=', self.company_id.id)
#                                 ], limit=1)
#                                 if warehouse:
#                                     self.warehouse_id = warehouse
#                                     _logger.info(
#                                         f"Auto-set warehouse to {warehouse.name} from analytic account {analytic_account.name}")
#                                     break
#                         except Exception as e:
#                             _logger.warning(f"Error auto-setting warehouse from analytic: {str(e)}")
#                             pass
#
#     def action_post(self):
#         """Override to handle CUSTOMER invoices and credit notes ONLY"""
#         res = super(AccountMove, self).action_post()
#
#         for invoice in self:
#             _logger.info(f"🟢 INVOICE MODULE - Processing: {invoice.name}, Type: {invoice.move_type}")
#
#             # ═══════════════════════════════════════════════════════════════
#             # CRITICAL: ONLY HANDLE CUSTOMER TRANSACTIONS (out_invoice, out_refund)
#             # Let direct_purchase_with_stock handle vendor transactions (in_invoice, in_refund)
#             # ═══════════════════════════════════════════════════════════════
#
#             # CUSTOMER INVOICE - Create delivery and reduce stock
#             if invoice.move_type == 'out_invoice' and invoice.create_delivery and not invoice.picking_id:
#                 try:
#                     _logger.info(f"🟢 INVOICE: Creating DELIVERY for customer invoice: {invoice.name}")
#                     invoice._create_delivery_from_invoice()
#                 except Exception as e:
#                     _logger.error(f"Error creating delivery order for invoice {invoice.name}: {str(e)}")
#                     raise UserError(_(f"Failed to create delivery order: {str(e)}"))
#
#             # CUSTOMER CREDIT NOTE - Create return and add stock back
#             elif invoice.move_type == 'out_refund' and invoice.create_delivery and not invoice.picking_id:
#                 try:
#                     _logger.info(f"🟢 INVOICE: Creating CUSTOMER RETURN for credit note: {invoice.name}")
#                     invoice._create_customer_return_from_refund()
#                 except Exception as e:
#                     _logger.error(f"Error creating return for credit note {invoice.name}: {str(e)}")
#                     raise UserError(_(f"Failed to create stock return: {str(e)}"))
#
#         return res
#
#     def button_cancel(self):
#         """Override cancel to properly handle delivery orders"""
#         for invoice in self:
#             # ONLY handle customer transactions
#             if invoice.move_type not in ['out_invoice', 'out_refund']:
#                 continue
#
#             if invoice.picking_id:
#                 if invoice.picking_id.state == 'done':
#                     raise UserError(_(
#                         "⚠️ CANNOT CANCEL INVOICE\n\n"
#                         "Invoice: %s\n"
#                         "Delivery Order: %s is already VALIDATED\n"
#                         "Stock has been reduced from warehouse!\n\n"
#                         "╔═══════════════════════════════╗\n"
#                         "To cancel this invoice properly:\n"
#                         "╚═══════════════════════════════╝\n\n"
#                         "Option 1: CREATE A CREDIT NOTE\n"
#                         "   • Go to invoice and click 'Add Credit Note'\n"
#                         "   • This will reverse the accounting entry\n"
#                         "   • If you want stock back, check 'Create Delivery Order'\n\n"
#                         "Option 2: MANUAL RETURN (Inventory)\n"
#                         "   • Go to Inventory → Returns\n"
#                         "   • Create return for delivery %s\n"
#                         "   • Then you can cancel this invoice\n\n"
#                         "This protection prevents inventory discrepancies."
#                     ) % (invoice.name, invoice.picking_id.name, invoice.picking_id.name))
#
#                 elif invoice.picking_id.state in ['confirmed', 'assigned', 'waiting']:
#                     picking_name = invoice.picking_id.name
#                     _logger.info(f"Cancelling unvalidated delivery {picking_name} for invoice {invoice.name}")
#
#                     try:
#                         invoice.picking_id.action_cancel()
#                         invoice.picking_id.unlink()
#                         invoice.picking_id = False
#
#                         self.message_post(body=_(
#                             "✅ Delivery order %s was cancelled and removed successfully.\n"
#                             "No stock movement occurred."
#                         ) % picking_name)
#
#                         _logger.info(f"Successfully cancelled and removed delivery {picking_name}")
#                     except Exception as e:
#                         _logger.error(f"Error cancelling delivery {picking_name}: {str(e)}")
#                         raise UserError(_(
#                             "Error cancelling delivery order %s: %s"
#                         ) % (picking_name, str(e)))
#
#         return super(AccountMove, self).button_cancel()
#
#     def _create_delivery_from_invoice(self):
#         """Create and validate delivery order from invoice with stock checking"""
#         self.ensure_one()
#
#         _logger.info(f"🟢 INVOICE: Starting delivery creation for invoice: {self.name}")
#
#         # Filter stockable products
#         stockable_lines = []
#         for line in self.invoice_line_ids:
#             if (line.product_id and
#                     line.product_id.type != 'service' and
#                     line.quantity > 0 and
#                     line.display_type not in ['line_section', 'line_note']):
#                 stockable_lines.append(line)
#                 _logger.info(f"   ✓ Line accepted: {line.product_id.name}")
#
#         if not stockable_lines:
#             error_msg = 'No stockable products found for delivery creation.\n\nProducts found:\n'
#             for line in self.invoice_line_ids:
#                 if line.product_id:
#                     error_msg += f"- {line.product_id.name}: Type={line.product_id.type}\n"
#             raise UserError(_(error_msg))
#
#         # Get warehouse
#         warehouse = self._get_warehouse()
#
#         location_id = warehouse.lot_stock_id.id
#
#         # ═══════════════════════════════════════════════════════════════
#         # STOCK AVAILABILITY CHECK
#         # ═══════════════════════════════════════════════════════════════
#         stock_warnings = []
#         is_stock_manager = self.env.user.has_group('stock.group_stock_manager')
#
#         for line in stockable_lines:
#             available_qty = line.product_id.with_context(
#                 location=location_id
#             ).qty_available
#
#             if available_qty < line.quantity:
#                 shortage = line.quantity - available_qty
#                 warning_msg = _(
#                     "⚠️ LOW STOCK ALERT\n"
#                     "┌───────────────────────────────┐\n"
#                     "Product: %s\n"
#                     "Available Stock: %.2f %s\n"
#                     "Requested Quantity: %.2f %s\n"
#                     "Shortage: %.2f %s\n"
#                     "Warehouse: %s\n"
#                     "└───────────────────────────────┘"
#                 ) % (
#                                   line.product_id.name,
#                                   available_qty, line.product_uom_id.name,
#                                   line.quantity, line.product_uom_id.name,
#                                   shortage, line.product_uom_id.name,
#                                   warehouse.name
#                               )
#
#                 stock_warnings.append({
#                     'product': line.product_id.name,
#                     'available': available_qty,
#                     'requested': line.quantity,
#                     'shortage': shortage,
#                     'message': warning_msg
#                 })
#
#         if stock_warnings:
#             if not is_stock_manager:
#                 error_messages = "\n\n".join([w['message'] for w in stock_warnings])
#                 raise UserError(_(
#                     "%s\n\n"
#                     "❌ INSUFFICIENT STOCK\n"
#                     "You don't have permission to create deliveries with insufficient stock."
#                 ) % error_messages)
#             else:
#                 warning_summary = "⚠️ NEGATIVE STOCK WARNING - Manager Override\n\n"
#                 for w in stock_warnings:
#                     warning_summary += f"• {w['product']}: Short by {w['shortage']:.2f}\n"
#
#                 self.message_post(
#                     body=warning_summary,
#                     message_type='notification',
#                     subtype_xmlid='mail.mt_note'
#                 )
#                 _logger.warning(f"Negative stock allowed by manager for invoice {self.name}")
#
#         # Get customer location
#         customer_location = self.env.ref('stock.stock_location_customers', raise_if_not_found=False)
#         if not customer_location:
#             customer_location = self.env['stock.location'].search([
#                 ('usage', '=', 'customer')
#             ], limit=1)
#
#         if not customer_location:
#             raise UserError(_('Customer location not found'))
#
#         location_dest_id = customer_location.id
#
#         _logger.info(f"   📦 FROM: {warehouse.lot_stock_id.complete_name} → TO: {customer_location.complete_name}")
#
#         # Use OUTGOING picking type
#         picking_type = warehouse.out_type_id
#
#         if not picking_type:
#             raise UserError(_('Delivery operation type not found in warehouse %s') % warehouse.name)
#
#         # Create picking
#         picking_vals = {
#             'picking_type_id': picking_type.id,
#             'partner_id': self.partner_id.id,
#             'origin': self.name,
#             'location_id': location_id,
#             'location_dest_id': location_dest_id,
#             'move_type': 'direct',
#             'company_id': self.company_id.id,
#         }
#
#         picking = self.env['stock.picking'].create(picking_vals)
#         _logger.info(f"   Created picking: {picking.name} from warehouse: {warehouse.name}")
#
#         # Create stock moves
#         self._create_stock_moves(picking, stockable_lines, location_id, location_dest_id, picking_type)
#
#         # Validate picking
#         self._validate_picking(picking)
#
#         # Link picking to invoice
#         self.picking_id = picking.id
#         _logger.info(f"   Successfully linked picking {picking.name} to invoice {self.name}")
#
#         # Success message
#         message = _('✅ Delivery order %s created and validated from warehouse %s') % (
#             picking.name, warehouse.name)
#         self.message_post(body=message)
#
#         return picking
#
#     def _create_customer_return_from_refund(self):
#         """
#         🟢 CUSTOMER RETURN: Receive goods FROM customer (ADDS stock to warehouse)
#
#         Flow: Customers → Warehouse Stock
#         This INCREASES inventory
#         """
#         self.ensure_one()
#
#         _logger.info(f"🟢 INVOICE: Starting CUSTOMER return for credit note: {self.name}")
#
#         # Filter stockable products
#         stockable_lines = []
#         for line in self.invoice_line_ids:
#             if (line.product_id and
#                     line.product_id.type != 'service' and
#                     line.quantity > 0 and
#                     line.display_type not in ['line_section', 'line_note']):
#                 stockable_lines.append(line)
#                 _logger.info(f"   ✓ Product: {line.product_id.name} - Qty: {line.quantity}")
#
#         if not stockable_lines:
#             raise UserError(_('No stockable products found for return creation'))
#
#         # Get warehouse
#         warehouse = self._get_warehouse()
#
#         # ═══════════════════════════════════════════════════════════════
#         # CRITICAL: CUSTOMER RETURN LOCATIONS
#         # ═══════════════════════════════════════════════════════════════
#
#         # Source: CUSTOMER location (where we're receiving stock FROM)
#         customer_location = self.env.ref('stock.stock_location_customers', raise_if_not_found=False)
#         if not customer_location:
#             customer_location = self.env['stock.location'].search([
#                 ('usage', '=', 'customer')
#             ], limit=1)
#
#         if not customer_location:
#             raise UserError(_('Customer location not found'))
#
#         location_id = customer_location.id
#         _logger.info(f"   📍 FROM (source): {customer_location.complete_name}")
#
#         # Destination: OUR warehouse (where we're adding stock TO)
#         location_dest_id = warehouse.lot_stock_id.id
#         _logger.info(f"   📍 TO (destination): {warehouse.lot_stock_id.complete_name}")
#
#         # Use INCOMING picking type for customer returns (goods entering warehouse)
#         picking_type = warehouse.in_type_id
#
#         if not picking_type:
#             raise UserError(_('Receipt operation type not found in warehouse %s') % warehouse.name)
#
#         _logger.info(f"   📦 Picking type: {picking_type.name} (code: {picking_type.code})")
#         _logger.info(f"   🟢 This will ADD stock to warehouse")
#
#         # Create return picking
#         picking_vals = {
#             'picking_type_id': picking_type.id,
#             'partner_id': self.partner_id.id,
#             'origin': self.name + ' (Customer Return)',
#             'location_id': location_id,  # FROM customer
#             'location_dest_id': location_dest_id,  # TO warehouse
#             'move_type': 'direct',
#             'company_id': self.company_id.id,
#         }
#
#         picking = self.env['stock.picking'].create(picking_vals)
#         _logger.info(f"   🟢 Created CUSTOMER RETURN picking: {picking.name}")
#
#         # Create stock moves
#         self._create_stock_moves(picking, stockable_lines, location_id, location_dest_id, picking_type)
#
#         # Validate picking
#         self._validate_picking(picking)
#
#         # Link return to credit note
#         self.picking_id = picking.id
#
#         message = _('✅ Customer Return %s created - Products returned FROM customer TO warehouse\n'
#                     'Warehouse: %s\n'
#                     'Stock INCREASED by return') % (picking.name, warehouse.name)
#         self.message_post(body=message)
#
#         _logger.info(f"   🟢 CUSTOMER RETURN completed - Stock ADDED to {warehouse.name}")
#         return picking
#
#     def _get_warehouse(self):
#         """Get warehouse for stock operations"""
#         if self.warehouse_id:
#             return self.warehouse_id
#
#         # Try to get from analytic account
#         warehouse = None
#         if self.invoice_line_ids and self.invoice_line_ids[0].analytic_distribution:
#             analytic_dict = self.invoice_line_ids[0].analytic_distribution
#             if analytic_dict:
#                 analytic_id = int(list(analytic_dict.keys())[0])
#                 analytic_account = self.env['account.analytic.account'].browse(analytic_id)
#                 if analytic_account:
#                     warehouse = self.env['stock.warehouse'].search([
#                         ('name', 'ilike', analytic_account.name),
#                         ('company_id', '=', self.company_id.id)
#                     ], limit=1)
#
#         if not warehouse:
#             warehouse = self.env['stock.warehouse'].search([
#                 ('company_id', '=', self.company_id.id)
#             ], limit=1)
#
#         if not warehouse:
#             raise UserError(_('No warehouse found for company %s') % self.company_id.name)
#
#         return warehouse
#
#     def _create_stock_moves(self, picking, stockable_lines, location_id, location_dest_id, picking_type):
#         """Create stock moves for picking"""
#         moves_created = 0
#         for line in stockable_lines:
#             move_vals = {
#                 # 'name' is auto-computed in Odoo 19 - DO NOT SET IT
#                 'product_id': line.product_id.id,
#                 'product_uom_qty': line.quantity,
#                 'product_uom': line.product_uom_id.id,
#                 'picking_id': picking.id,
#                 'location_id': location_id,
#                 'location_dest_id': location_dest_id,
#                 'company_id': self.company_id.id,
#                 'picking_type_id': picking_type.id,
#             }
#
#             move = self.env['stock.move'].create(move_vals)
#             moves_created += 1
#             _logger.info(f"   ✓ Created move: {line.product_id.name} - Qty: {line.quantity}")
#
#         if moves_created == 0:
#             picking.unlink()
#             raise UserError(_('No stock moves could be created'))
#
#     def _validate_picking(self, picking):
#         """Confirm and validate picking"""
#         picking.action_confirm()
#
#         if picking.state != 'assigned':
#             picking.action_assign()
#
#         for move in picking.move_ids:
#             move.quantity = move.product_uom_qty
#
#         try:
#             result = picking.button_validate()
#
#             if isinstance(result, dict) and result.get('res_model') == 'stock.backorder.confirmation':
#                 backorder_wizard = self.env['stock.backorder.confirmation'].browse(result.get('res_id'))
#                 backorder_wizard.process_cancel_backorder()
#         except Exception as e:
#             _logger.error(f"Error validating picking: {str(e)}")
#             raise UserError(_(f"Error validating picking: {str(e)}"))
#
#     def action_view_delivery(self):
#         """Smart button to view related delivery order or return"""
#         self.ensure_one()
#
#         if not self.picking_id or not self.picking_id.exists():
#             raise UserError(_('No delivery order found or it has been deleted'))
#
#         return {
#             'type': 'ir.actions.act_window',
#             'name': _('Delivery Order'),
#             'res_model': 'stock.picking',
#             'res_id': self.picking_id.id,
#             'view_mode': 'form',
#             'target': 'current',
#         }

# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from collections import defaultdict
import logging

_logger = logging.getLogger(__name__)


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

    @api.onchange('analytic_distribution')
    def _onchange_analytic_distribution_set_warehouse(self):
        """Auto-set warehouse when analytic account is selected"""
        if self.analytic_distribution and self.move_id and self.move_id.move_type in ['out_invoice', 'out_refund']:
            analytic_dict = self.analytic_distribution
            if analytic_dict:
                try:
                    analytic_id = int(list(analytic_dict.keys())[0])
                    analytic_account = self.env['account.analytic.account'].browse(analytic_id)

                    if analytic_account:
                        # Search for warehouse with matching name
                        warehouse = self.env['stock.warehouse'].search([
                            ('name', 'ilike', analytic_account.name),
                            ('company_id', '=', self.move_id.company_id.id)
                        ], limit=1)

                        if warehouse and not self.warehouse_id:
                            self.warehouse_id = warehouse
                            _logger.info(f"Auto-set warehouse to {warehouse.name} from analytic account")

                except Exception as e:
                    _logger.warning(f"Error auto-setting warehouse from analytic: {str(e)}")


class AccountMove(models.Model):
    _inherit = 'account.move'

    picking_id = fields.Many2one('stock.picking', string='Delivery Order', readonly=True, copy=False)
    create_delivery = fields.Boolean(
        string='Create Delivery Order',
        default=False,
        help='Check this to automatically create delivery order on invoice validation'
    )
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Default Warehouse',
        help='Default warehouse if lines do not have specific warehouses'
    )

    @api.onchange('invoice_line_ids')
    def _onchange_invoice_lines_set_warehouse(self):
        """Auto-set default warehouse based on analytic account"""
        if self.move_type not in ['out_invoice', 'out_refund']:
            return

        if self.invoice_line_ids and not self.warehouse_id:
            for line in self.invoice_line_ids:
                if line.analytic_distribution:
                    analytic_dict = line.analytic_distribution
                    if analytic_dict:
                        try:
                            analytic_id = int(list(analytic_dict.keys())[0])
                            analytic_account = self.env['account.analytic.account'].browse(analytic_id)
                            if analytic_account:
                                warehouse = self.env['stock.warehouse'].search([
                                    ('name', 'ilike', analytic_account.name),
                                    ('company_id', '=', self.company_id.id)
                                ], limit=1)
                                if warehouse:
                                    self.warehouse_id = warehouse
                                    _logger.info(f"Auto-set default warehouse to {warehouse.name}")
                                    break
                        except Exception as e:
                            _logger.warning(f"Error auto-setting warehouse: {str(e)}")

    def action_post(self):
        """Override to handle CUSTOMER invoices and credit notes ONLY"""
        res = super(AccountMove, self).action_post()

        for invoice in self:
            _logger.info(f"🟢 Processing: {invoice.name}, Type: {invoice.move_type}")

            # CUSTOMER INVOICE - Create delivery and reduce stock
            if invoice.move_type == 'out_invoice' and invoice.create_delivery and not invoice.picking_id:
                try:
                    _logger.info(f"🟢 Creating DELIVERY for invoice: {invoice.name}")
                    invoice._create_delivery_from_invoice()
                except Exception as e:
                    _logger.error(f"Error creating delivery: {str(e)}")
                    raise UserError(_(f"Failed to create delivery order: {str(e)}"))

            # CUSTOMER CREDIT NOTE - Create return and add stock back
            elif invoice.move_type == 'out_refund' and invoice.create_delivery and not invoice.picking_id:
                try:
                    _logger.info(f"🟢 Creating RETURN for credit note: {invoice.name}")
                    invoice._create_customer_return_from_refund()
                except Exception as e:
                    _logger.error(f"Error creating return: {str(e)}")
                    raise UserError(_(f"Failed to create stock return: {str(e)}"))

        return res

    def button_cancel(self):
        """Override cancel to properly handle delivery orders"""
        for invoice in self:
            if invoice.move_type not in ['out_invoice', 'out_refund']:
                continue

            if invoice.picking_id:
                if invoice.picking_id.state == 'done':
                    raise UserError(_(
                        "⚠️ CANNOT CANCEL INVOICE\n\n"
                        "Invoice: %s\n"
                        "Delivery Order: %s is already VALIDATED\n"
                        "Stock has been moved!\n\n"
                        "To cancel properly:\n"
                        "Option 1: CREATE A CREDIT NOTE\n"
                        "Option 2: MANUAL RETURN in Inventory"
                    ) % (invoice.name, invoice.picking_id.name))

                elif invoice.picking_id.state in ['confirmed', 'assigned', 'waiting']:
                    picking_name = invoice.picking_id.name
                    try:
                        invoice.picking_id.action_cancel()
                        invoice.picking_id.unlink()
                        invoice.picking_id = False
                        self.message_post(body=_("✅ Delivery %s cancelled") % picking_name)
                    except Exception as e:
                        raise UserError(_("Error cancelling delivery %s: %s") % (picking_name, str(e)))

        return super(AccountMove, self).button_cancel()

    def _create_delivery_from_invoice(self):
        """
        🔑 KEY CHANGE: Create deliveries grouped by warehouse from invoice line warehouses
        """
        self.ensure_one()

        _logger.info(f"🟢 Starting delivery creation for invoice: {self.name}")

        # Filter stockable products
        stockable_lines = []
        for line in self.invoice_line_ids:
            if (line.product_id and
                    line.product_id.type != 'service' and
                    line.quantity > 0 and
                    line.display_type not in ['line_section', 'line_note']):
                stockable_lines.append(line)

        if not stockable_lines:
            raise UserError(_('No stockable products found for delivery'))

        # 🔑 GROUP LINES BY WAREHOUSE (from invoice_line.warehouse_id)
        lines_by_warehouse = defaultdict(list)
        default_warehouse = self.warehouse_id or self._get_default_warehouse()

        for line in stockable_lines:
            # Use line's warehouse if set, otherwise use default
            warehouse = line.warehouse_id or default_warehouse
            lines_by_warehouse[warehouse].append(line)
            _logger.info(f"   📦 Product: {line.product_id.name} → Warehouse: {warehouse.name}")

        _logger.info(f"   🏢 Total warehouses involved: {len(lines_by_warehouse)}")

        # Create separate picking for each warehouse
        pickings = []
        for warehouse, lines in lines_by_warehouse.items():
            _logger.info(f"\n   🏭 Creating picking for warehouse: {warehouse.name}")

            picking = self._create_picking_for_warehouse(
                warehouse,
                lines,
                is_delivery=True
            )
            pickings.append(picking)

        # Link first picking to invoice (for smart button)
        if pickings:
            self.picking_id = pickings[0].id

        # Success message
        warehouse_names = ", ".join([p.location_id.warehouse_id.name for p in pickings])
        message = _('✅ Created %d delivery order(s) from warehouses: %s') % (len(pickings), warehouse_names)
        self.message_post(body=message)

        return pickings

    def _create_customer_return_from_refund(self):
        """
        🔑 Create returns grouped by warehouse from invoice line warehouses
        """
        self.ensure_one()

        _logger.info(f"🟢 Starting RETURN for credit note: {self.name}")

        # Filter stockable products
        stockable_lines = []
        for line in self.invoice_line_ids:
            if (line.product_id and
                    line.product_id.type != 'service' and
                    line.quantity > 0 and
                    line.display_type not in ['line_section', 'line_note']):
                stockable_lines.append(line)

        if not stockable_lines:
            raise UserError(_('No stockable products found for return'))

        # GROUP LINES BY WAREHOUSE
        lines_by_warehouse = defaultdict(list)
        default_warehouse = self.warehouse_id or self._get_default_warehouse()

        for line in stockable_lines:
            warehouse = line.warehouse_id or default_warehouse
            lines_by_warehouse[warehouse].append(line)

        # Create return picking for each warehouse
        pickings = []
        for warehouse, lines in lines_by_warehouse.items():
            picking = self._create_picking_for_warehouse(
                warehouse,
                lines,
                is_delivery=False  # This is a return
            )
            pickings.append(picking)

        if pickings:
            self.picking_id = pickings[0].id

        warehouse_names = ", ".join([p.location_dest_id.warehouse_id.name for p in pickings])
        message = _('✅ Created %d return order(s) to warehouses: %s') % (len(pickings), warehouse_names)
        self.message_post(body=message)

        return pickings

    def _create_picking_for_warehouse(self, warehouse, lines, is_delivery=True):
        """
        Create a single picking for given warehouse and lines

        Args:
            warehouse: stock.warehouse record
            lines: list of account.move.line records
            is_delivery: True for delivery (reduce stock), False for return (add stock)
        """
        # Get locations based on operation type
        if is_delivery:
            # DELIVERY: Warehouse → Customer
            location_id = warehouse.lot_stock_id.id
            customer_location = self.env.ref('stock.stock_location_customers')
            location_dest_id = customer_location.id
            picking_type = warehouse.out_type_id
            operation_name = "Delivery"
        else:
            # RETURN: Customer → Warehouse
            customer_location = self.env.ref('stock.stock_location_customers')
            location_id = customer_location.id
            location_dest_id = warehouse.lot_stock_id.id
            picking_type = warehouse.in_type_id
            operation_name = "Return"

        _logger.info(f"   📍 FROM: {location_id} → TO: {location_dest_id}")

        # Check stock availability for deliveries
        if is_delivery:
            self._check_stock_availability(lines, warehouse.lot_stock_id.id)

        # Create picking
        picking_vals = {
            'picking_type_id': picking_type.id,
            'partner_id': self.partner_id.id,
            'origin': f"{self.name} ({operation_name} - {warehouse.name})",
            'location_id': location_id,
            'location_dest_id': location_dest_id,
            'move_type': 'direct',
            'company_id': self.company_id.id,
        }

        picking = self.env['stock.picking'].create(picking_vals)
        _logger.info(f"   ✅ Created picking: {picking.name}")

        # Create stock moves
        for line in lines:
            move_vals = {
                'product_id': line.product_id.id,
                'product_uom_qty': line.quantity,
                'product_uom': line.product_uom_id.id,
                'picking_id': picking.id,
                'location_id': location_id,
                'location_dest_id': location_dest_id,
                'company_id': self.company_id.id,
                'picking_type_id': picking_type.id,
            }
            self.env['stock.move'].create(move_vals)
            _logger.info(f"      ✓ Move: {line.product_id.name} x {line.quantity}")

        # Validate picking
        self._validate_picking(picking)

        return picking

    def _check_stock_availability(self, lines, location_id):
        """Check stock availability and warn/block if insufficient"""
        stock_warnings = []
        is_stock_manager = self.env.user.has_group('stock.group_stock_manager')

        for line in lines:
            available_qty = line.product_id.with_context(
                location=location_id
            ).qty_available

            if available_qty < line.quantity:
                shortage = line.quantity - available_qty
                stock_warnings.append({
                    'product': line.product_id.name,
                    'available': available_qty,
                    'requested': line.quantity,
                    'shortage': shortage,
                })

        if stock_warnings:
            error_msg = "⚠️ LOW STOCK ALERT\n" + "─" * 31 + "\n"
            for w in stock_warnings:
                error_msg += f"Product: {w['product']}\n"
                error_msg += f"Available: {w['available']:.2f}\n"
                error_msg += f"Requested: {w['requested']:.2f}\n"
                error_msg += f"Shortage: {w['shortage']:.2f}\n"
                error_msg += "─" * 31 + "\n"

            if not is_stock_manager:
                raise UserError(_(
                    "%s\n❌ INSUFFICIENT STOCK\n"
                    "You don't have permission to create deliveries with insufficient stock."
                ) % error_msg)
            else:
                self.message_post(body=error_msg)
                _logger.warning(f"Negative stock allowed by manager for {self.name}")

    def _get_default_warehouse(self):
        """Get default warehouse for company"""
        warehouse = self.env['stock.warehouse'].search([
            ('company_id', '=', self.company_id.id)
        ], limit=1)

        if not warehouse:
            raise UserError(_('No warehouse found for company %s') % self.company_id.name)

        return warehouse

    def _validate_picking(self, picking):
        """Confirm and validate picking"""
        picking.action_confirm()

        if picking.state != 'assigned':
            picking.action_assign()

        for move in picking.move_ids:
            move.quantity = move.product_uom_qty

        try:
            result = picking.button_validate()

            if isinstance(result, dict) and result.get('res_model') == 'stock.backorder.confirmation':
                backorder_wizard = self.env['stock.backorder.confirmation'].browse(result.get('res_id'))
                backorder_wizard.process_cancel_backorder()
        except Exception as e:
            _logger.error(f"Error validating picking: {str(e)}")
            raise UserError(_(f"Error validating picking: {str(e)}"))

    def action_view_delivery(self):
        """Smart button to view related delivery orders"""
        self.ensure_one()

        # Find all pickings related to this invoice
        pickings = self.env['stock.picking'].search([
            ('origin', 'ilike', self.name)
        ])

        if not pickings:
            raise UserError(_('No delivery orders found'))

        if len(pickings) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Delivery Order'),
                'res_model': 'stock.picking',
                'res_id': pickings.id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Delivery Orders'),
                'res_model': 'stock.picking',
                'domain': [('id', 'in', pickings.ids)],
                'view_mode': 'tree,form',
                'target': 'current',
            }
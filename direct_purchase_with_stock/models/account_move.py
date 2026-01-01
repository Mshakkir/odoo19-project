# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    receipt_id = fields.Many2one('stock.picking', string='Receipt', readonly=True, copy=False)
    create_receipt = fields.Boolean(
        string='Create Receipt',
        default=False,
        help='Check this to automatically create stock receipt on bill validation'
    )
    purchase_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Receiving Warehouse',
        help='Select warehouse for stock receipt. If not set, default warehouse will be used.'
    )

    @api.onchange('invoice_line_ids')
    def _onchange_invoice_lines_set_purchase_warehouse(self):
        """Auto-set warehouse based on analytic account from bill lines"""
        if self.invoice_line_ids and not self.purchase_warehouse_id:
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
                                    self.purchase_warehouse_id = warehouse
                                    _logger.info(
                                        f"Auto-set warehouse to {warehouse.name} from analytic account {analytic_account.name}")
                                    break
                        except Exception as e:
                            _logger.warning(f"Error auto-setting warehouse from analytic: {str(e)}")
                            pass

    def action_post(self):
        """Override to handle vendor bills, refunds, and stock movements"""
        res = super(AccountMove, self).action_post()

        for bill in self:
            _logger.info(f"=== PROCESSING BILL POST: {bill.name} ===")
            _logger.info(f"Move Type: {bill.move_type}")
            _logger.info(f"Create Receipt Enabled: {bill.create_receipt}")
            _logger.info(f"Already has receipt: {bool(bill.receipt_id)}")

            # VENDOR BILL - Create receipt and add stock
            if bill.move_type == 'in_invoice' and bill.create_receipt and not bill.receipt_id:
                try:
                    _logger.info(f"✓ BRANCH: Creating RECEIPT for vendor bill (stock IN): {bill.name}")
                    bill._create_receipt_from_bill()
                except Exception as e:
                    _logger.error(f"Error creating receipt for bill {bill.name}: {str(e)}")
                    raise UserError(_(f"Failed to create receipt: {str(e)}"))

            # VENDOR REFUND - Create return and remove stock
            elif bill.move_type == 'in_refund' and bill.create_receipt and not bill.receipt_id:
                try:
                    _logger.info(f"✓ BRANCH: Creating RETURN for vendor refund (stock OUT): {bill.name}")
                    bill._create_return_from_refund()
                except Exception as e:
                    _logger.error(f"Error creating return for refund {bill.name}: {str(e)}")
                    raise UserError(_(f"Failed to create return: {str(e)}"))
            else:
                _logger.info(f"✗ No automatic stock movement for this document")

        return res

    def button_cancel(self):
        """
        Override cancel to properly handle receipts and prevent stock inconsistencies
        """
        for bill in self:
            if bill.receipt_id:
                if bill.receipt_id.state == 'done':
                    # Stock already received - CANNOT auto-reverse
                    raise UserError(_(
                        "⚠️ CANNOT CANCEL BILL\n\n"
                        "Bill: %s\n"
                        "Receipt: %s is already VALIDATED\n"
                        "Stock has been added to warehouse!\n\n"
                        "╔══════════════════════════════╗\n"
                        "To cancel this bill properly:\n"
                        "╚══════════════════════════════╝\n\n"
                        "Option 1: CREATE A VENDOR REFUND\n"
                        "   • Go to bill and click 'Add Refund'\n"
                        "   • This will reverse the accounting entry\n"
                        "   • If you want to return stock, check 'Create Receipt'\n\n"
                        "Option 2: MANUAL RETURN (Inventory)\n"
                        "   • Go to Inventory → Returns\n"
                        "   • Create return for receipt %s\n"
                        "   • Then you can cancel this bill\n\n"
                        "This protection prevents inventory discrepancies."
                    ) % (bill.name, bill.receipt_id.name, bill.receipt_id.name))

                elif bill.receipt_id.state in ['confirmed', 'assigned', 'waiting']:
                    # Receipt exists but NOT validated yet - safe to cancel
                    receipt_name = bill.receipt_id.name
                    _logger.info(f"Cancelling unvalidated receipt {receipt_name} for bill {bill.name}")

                    try:
                        bill.receipt_id.action_cancel()
                        bill.receipt_id.unlink()
                        bill.receipt_id = False

                        self.message_post(body=_(
                            "✅ Receipt %s was cancelled and removed successfully.\n"
                            "No stock movement occurred."
                        ) % receipt_name)

                        _logger.info(f"Successfully cancelled and removed receipt {receipt_name}")
                    except Exception as e:
                        _logger.error(f"Error cancelling receipt {receipt_name}: {str(e)}")
                        raise UserError(_(
                            "Error cancelling receipt %s: %s"
                        ) % (receipt_name, str(e)))

        return super(AccountMove, self).button_cancel()

    def _create_receipt_from_bill(self):
        """Create and validate stock receipt from vendor bill"""
        self.ensure_one()

        _logger.info(f"Starting receipt creation for bill: {self.name}")

        # Filter stockable products
        stockable_lines = []
        for line in self.invoice_line_ids:
            if (line.product_id and
                    line.product_id.type != 'service' and
                    line.quantity > 0 and
                    line.display_type not in ['line_section', 'line_note']):
                stockable_lines.append(line)
                _logger.info(f"✓ Line accepted: {line.product_id.name}")

        if not stockable_lines:
            error_msg = 'No stockable products found for receipt creation.\n\nProducts found:\n'
            for line in self.invoice_line_ids:
                if line.product_id:
                    error_msg += f"- {line.product_id.name}: Type={line.product_id.type}\n"
            raise UserError(_(error_msg))

        # Get warehouse
        if self.purchase_warehouse_id:
            warehouse = self.purchase_warehouse_id
        else:
            warehouse = None
            if self.invoice_line_ids and self.invoice_line_ids[0].analytic_distribution:
                analytic_dict = self.invoice_line_ids[0].analytic_distribution
                if analytic_dict:
                    analytic_id = int(list(analytic_dict.keys())[0])
                    analytic_account = self.env['account.analytic.account'].browse(analytic_id)
                    if analytic_account:
                        warehouse = self.env['stock.warehouse'].search([
                            ('name', 'ilike', analytic_account.name),
                            ('company_id', '=', self.company_id.id)
                        ], limit=1)

            if not warehouse:
                warehouse = self.env['stock.warehouse'].search([
                    ('company_id', '=', self.company_id.id)
                ], limit=1)

        if not warehouse:
            raise UserError(_('No warehouse found for company %s') % self.company_id.name)

        # For receipts: Vendor location → Warehouse
        location_dest_id = warehouse.lot_stock_id.id

        vendor_location = self.env.ref('stock.stock_location_suppliers', raise_if_not_found=False)
        if not vendor_location:
            vendor_location = self.env['stock.location'].search([
                ('usage', '=', 'supplier')
            ], limit=1)

        if not vendor_location:
            raise UserError(_('Vendor location not found'))

        location_id = vendor_location.id

        # Use incoming picking type for receipts
        picking_type = warehouse.in_type_id

        if not picking_type:
            raise UserError(_('Receipt operation type not found in warehouse %s') % warehouse.name)

        # Create receipt picking
        picking_vals = {
            'picking_type_id': picking_type.id,
            'partner_id': self.partner_id.id,
            'origin': self.name,
            'location_id': location_id,
            'location_dest_id': location_dest_id,
            'move_type': 'direct',
            'company_id': self.company_id.id,
        }

        picking = self.env['stock.picking'].create(picking_vals)
        _logger.info(f"Created receipt: {picking.name} for warehouse: {warehouse.name}")

        # Create stock moves
        moves_created = 0
        for line in stockable_lines:
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

            move = self.env['stock.move'].create(move_vals)
            moves_created += 1
            _logger.info(f"Created stock move: {move.id} - {line.product_id.name}")

        if moves_created == 0:
            picking.unlink()
            raise UserError(_('No stock moves could be created'))

        # Confirm and validate
        picking.action_confirm()

        if picking.state != 'assigned':
            picking.action_assign()

        # Set quantities done
        for move in picking.move_ids:
            move.quantity = move.product_uom_qty

        # Validate picking
        try:
            result = picking.button_validate()

            if isinstance(result, dict) and result.get('res_model') == 'stock.backorder.confirmation':
                backorder_wizard = self.env['stock.backorder.confirmation'].browse(result.get('res_id'))
                backorder_wizard.process_cancel_backorder()
        except Exception as e:
            _logger.error(f"Error validating receipt: {str(e)}")
            raise UserError(_(f"Error validating receipt: {str(e)}"))

        # Link receipt to bill
        self.receipt_id = picking.id
        _logger.info(f"Successfully linked receipt {picking.name} to bill {self.name}")

        # Success message
        message = _('✅ Receipt %s created and validated. Stock added to warehouse %s') % (
            picking.name, warehouse.name)
        self.message_post(body=message)

        return picking

    def _create_return_from_refund(self):
        """
        Create stock return for vendor refunds (return to vendor)
        Removes products from warehouse inventory
        """
        self.ensure_one()

        _logger.info(f"Starting return creation for vendor refund: {self.name}")

        # Filter stockable products
        stockable_lines = []
        for line in self.invoice_line_ids:
            if (line.product_id and
                    line.product_id.type != 'service' and
                    line.quantity > 0 and
                    line.display_type not in ['line_section', 'line_note']):
                stockable_lines.append(line)

        if not stockable_lines:
            raise UserError(_('No stockable products found for return creation'))

        # Get warehouse
        if self.purchase_warehouse_id:
            warehouse = self.purchase_warehouse_id
        else:
            warehouse = None
            if self.invoice_line_ids and self.invoice_line_ids[0].analytic_distribution:
                analytic_dict = self.invoice_line_ids[0].analytic_distribution
                if analytic_dict:
                    analytic_id = int(list(analytic_dict.keys())[0])
                    analytic_account = self.env['account.analytic.account'].browse(analytic_id)
                    if analytic_account:
                        warehouse = self.env['stock.warehouse'].search([
                            ('name', 'ilike', analytic_account.name),
                            ('company_id', '=', self.company_id.id)
                        ], limit=1)

            if not warehouse:
                warehouse = self.env['stock.warehouse'].search([
                    ('company_id', '=', self.company_id.id)
                ], limit=1)

        if not warehouse:
            raise UserError(_('No warehouse found for company %s') % self.company_id.name)

        # ════════════════════════════════════════════════════════
        # STOCK AVAILABILITY CHECK - Check before returning
        # ════════════════════════════════════════════════════════
        stock_warnings = []
        is_stock_manager = self.env.user.has_group('stock.group_stock_manager')

        source_location_id = warehouse.lot_stock_id.id

        for line in stockable_lines:
            # Get available quantity at warehouse location
            available_qty = line.product_id.with_context(
                location=source_location_id
            ).qty_available

            if available_qty < line.quantity:
                shortage = line.quantity - available_qty
                warning_msg = _(
                    "⚠️ INSUFFICIENT STOCK FOR RETURN\n"
                    "┌───────────────────────────────┐\n"
                    "Product: %s\n"
                    "Available Stock: %.2f %s\n"
                    "Return Quantity: %.2f %s\n"
                    "Shortage: %.2f %s\n"
                    "Warehouse: %s\n"
                    "└───────────────────────────────┘"
                ) % (
                                  line.product_id.name,
                                  available_qty, line.product_uom_id.name,
                                  line.quantity, line.product_uom_id.name,
                                  shortage, line.product_uom_id.name,
                                  warehouse.name
                              )

                stock_warnings.append({
                    'product': line.product_id.name,
                    'available': available_qty,
                    'requested': line.quantity,
                    'shortage': shortage,
                    'message': warning_msg
                })

        # Handle stock warnings
        if stock_warnings:
            if not is_stock_manager:
                # BLOCK regular users from creating negative stock
                error_messages = "\n\n".join([w['message'] for w in stock_warnings])
                raise UserError(_(
                    "%s\n\n"
                    "❌ CANNOT CREATE RETURN\n"
                    "┌───────────────────────────────┐\n"
                    "You don't have permission to return more stock than available.\n\n"
                    "Please contact your Inventory Manager or:\n"
                    "• Reduce refund quantities\n"
                    "• Check if products are in correct warehouse\n"
                    "• Verify stock before processing refund"
                ) % error_messages)
            else:
                # WARN managers but allow to proceed
                warning_summary = "⚠️ NEGATIVE STOCK WARNING - Manager Override\n\n"
                for w in stock_warnings:
                    warning_summary += f"• {w['product']}: Short by {w['shortage']:.2f}\n"

                self.message_post(
                    body=warning_summary,
                    message_type='notification',
                    subtype_xmlid='mail.mt_note'
                )
                _logger.warning(f"Negative stock allowed by manager for refund {self.name}: {warning_summary}")

        # ════════════════════════════════════════════════════════
        # CRITICAL FIX: Use INTERNAL transfer type, not delivery
        # This ensures stock is REMOVED, not ADDED
        # ════════════════════════════════════════════════════════

        # Get or create internal picking type for returns
        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'internal'),
            ('warehouse_id', '=', warehouse.id),
        ], limit=1)

        if not picking_type:
            # Fallback: use outgoing type but we'll force correct behavior
            picking_type = warehouse.out_type_id
            _logger.warning(f"No internal picking type found, using outgoing type for warehouse {warehouse.name}")

        if not picking_type:
            raise UserError(_('No suitable operation type found in warehouse %s') % warehouse.name)

        # For returns: Warehouse → Vendor location (stock LEAVES warehouse)
        location_id = warehouse.lot_stock_id.id

        vendor_location = self.env.ref('stock.stock_location_suppliers', raise_if_not_found=False)
        if not vendor_location:
            vendor_location = self.env['stock.location'].search([
                ('usage', '=', 'supplier')
            ], limit=1)

        if not vendor_location:
            raise UserError(_('Vendor location not found'))

        location_dest_id = vendor_location.id

        _logger.info(f"Creating return from {warehouse.lot_stock_id.name} to {vendor_location.name}")

        # Create return picking
        picking_vals = {
            'picking_type_id': picking_type.id,
            'partner_id': self.partner_id.id,
            'origin': self.name + ' (Return to Vendor)',
            'location_id': location_id,
            'location_dest_id': location_dest_id,
            'move_type': 'direct',
            'company_id': self.company_id.id,
        }

        picking = self.env['stock.picking'].create(picking_vals)
        _logger.info(f"Created return picking: {picking.name} for vendor refund {self.name}")

        # Create stock moves with explicit negative movement
        moves_created = 0
        for line in stockable_lines:
            _logger.info(f"Creating RETURN move for {line.product_id.name}")
            _logger.info(f"  Quantity to REMOVE: {line.quantity}")
            _logger.info(f"  From location ID: {location_id} ({warehouse.lot_stock_id.name})")
            _logger.info(f"  To location ID: {location_dest_id} ({vendor_location.name})")

            move_vals = {
                'name': f'Vendor Return: {line.product_id.name}',
                'product_id': line.product_id.id,
                'product_uom_qty': line.quantity,  # Positive quantity
                'product_uom': line.product_uom_id.id,
                'picking_id': picking.id,
                'location_id': location_id,  # FROM warehouse (stock will DECREASE here)
                'location_dest_id': location_dest_id,  # TO vendor (virtual)
                'company_id': self.company_id.id,
                'picking_type_id': picking_type.id,
                'state': 'draft',
            }

            move = self.env['stock.move'].create(move_vals)
            moves_created += 1

            _logger.info(f"✓ Created move ID {move.id}")
            _logger.info(f"  Move state: {move.state}")
            _logger.info(f"  Move from: {move.location_id.complete_name}")
            _logger.info(f"  Move to: {move.location_dest_id.complete_name}")

        if moves_created == 0:
            picking.unlink()
            raise UserError(_('No stock moves could be created for return'))

        _logger.info(f"Total return moves created: {moves_created}")

        # Confirm and validate
        picking.action_confirm()
        _logger.info(f"Return picking confirmed, state: {picking.state}")

        if picking.state != 'assigned':
            picking.action_assign()
            _logger.info(f"Return picking assigned, state: {picking.state}")

        # Set quantities done
        for move in picking.move_ids:
            move.quantity = move.product_uom_qty
            _logger.info(
                f"Set quantity done for {move.product_id.name}: {move.quantity} "
                f"(from {move.location_id.name} to {move.location_dest_id.name})"
            )

        try:
            result = picking.button_validate()
            _logger.info(f"Return picking validation result: {result}")

            if isinstance(result, dict) and result.get('res_model') == 'stock.backorder.confirmation':
                backorder_wizard = self.env['stock.backorder.confirmation'].browse(result.get('res_id'))
                backorder_wizard.process_cancel_backorder()
                _logger.info("Processed backorder wizard for return")
        except Exception as e:
            _logger.error(f"Error validating return: {str(e)}")
            raise UserError(_(f"Error validating return: {str(e)}"))

        # Link return to refund
        self.receipt_id = picking.id
        _logger.info(f"Successfully linked return picking {picking.name} to refund {self.name}")

        message = _('✅ Return %s created and validated. Products returned to vendor from warehouse %s') % (
            picking.name, warehouse.name)
        self.message_post(body=message)

        return picking

    def action_view_receipt(self):
        """Smart button to view related receipt or return"""
        self.ensure_one()

        if not self.receipt_id or not self.receipt_id.exists():
            raise UserError(_('No receipt found or it has been deleted'))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Receipt/Return'),
            'res_model': 'stock.picking',
            'res_id': self.receipt_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
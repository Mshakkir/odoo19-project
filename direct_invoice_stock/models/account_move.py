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
#
#     def action_post(self):
#         """Override the post method to create delivery order after invoice validation"""
#         res = super(AccountMove, self).action_post()
#
#         for invoice in self:
#             # Only for customer invoices (out_invoice) with create_delivery flag
#             if invoice.move_type == 'out_invoice' and invoice.create_delivery and not invoice.picking_id:
#                 try:
#                     _logger.info(f"Creating delivery order for invoice: {invoice.name}")
#                     invoice._create_delivery_from_invoice()
#                 except Exception as e:
#                     _logger.error(f"Error creating delivery order for invoice {invoice.name}: {str(e)}")
#                     raise UserError(_(f"Failed to create delivery order: {str(e)}"))
#
#         return res
#
#     def _create_delivery_from_invoice(self):
#         """Create and validate delivery order from invoice"""
#         self.ensure_one()
#
#         _logger.info(f"Starting delivery creation for invoice: {self.name}")
#
#         # Check if there are stockable products
#         # In Odoo, 'product' type means storable/goods, 'consu' means consumable, 'service' means service
#         stockable_lines = self.invoice_line_ids.filtered(
#             lambda l: l.product_id and l.product_id.type == 'product' and l.quantity > 0
#         )
#
#         if not stockable_lines:
#             _logger.warning(f"No stockable products found in invoice {self.name}")
#             # Log product types for debugging
#             for line in self.invoice_line_ids:
#                 if line.product_id:
#                     _logger.info(f"Product: {line.product_id.name}, Type: {line.product_id.type}")
#             raise UserError(
#                 _('No stockable products found in this invoice. Please add products with type "Storable Product" (Goods).'))
#
#         _logger.info(f"Found {len(stockable_lines)} stockable lines")
#
#         # Get warehouse
#         warehouse = self.env['stock.warehouse'].search([
#             ('company_id', '=', self.company_id.id)
#         ], limit=1)
#
#         if not warehouse:
#             _logger.error(f"No warehouse found for company {self.company_id.name}")
#             raise UserError(
#                 _('No warehouse found for company %s. Please create a warehouse first.') % self.company_id.name)
#
#         _logger.info(f"Using warehouse: {warehouse.name}")
#
#         # Get stock location
#         location_id = warehouse.lot_stock_id.id
#
#         # Get customer location
#         customer_location = self.env.ref('stock.stock_location_customers', raise_if_not_found=False)
#         if not customer_location:
#             # Fallback: search for customer location
#             customer_location = self.env['stock.location'].search([
#                 ('usage', '=', 'customer')
#             ], limit=1)
#
#         if not customer_location:
#             raise UserError(_('Customer location not found. Please check your stock configuration.'))
#
#         location_dest_id = customer_location.id
#
#         # Create picking (delivery order)
#         picking_type = warehouse.out_type_id
#
#         if not picking_type:
#             raise UserError(_('Delivery operation type not found in warehouse %s') % warehouse.name)
#
#         _logger.info(f"Creating picking with type: {picking_type.name}")
#
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
#         _logger.info(f"Created picking: {picking.name}")
#
#         # Create stock moves for each invoice line
#         moves_created = 0
#         for line in stockable_lines:
#             _logger.info(f"Creating move for product: {line.product_id.name}, qty: {line.quantity}")
#
#             move_vals = {
#                 'name': line.product_id.name or '/',
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
#             _logger.info(f"Created stock move: {move.name}")
#
#         if moves_created == 0:
#             picking.unlink()
#             raise UserError(_('No stock moves could be created.'))
#
#         _logger.info(f"Total moves created: {moves_created}")
#
#         # Confirm the picking
#         picking.action_confirm()
#         _logger.info("Picking confirmed")
#
#         # Check if picking is ready
#         if picking.state != 'assigned':
#             _logger.warning(f"Picking state is {picking.state}, attempting to force assign")
#             picking.action_assign()
#
#         # Auto-validate the picking (set quantities done)
#         for move in picking.move_ids:
#             for move_line in move.move_line_ids:
#                 move_line.quantity = move_line.reserved_uom_qty
#             # If no move lines, create them
#             if not move.move_line_ids:
#                 move._action_assign()
#                 for move_line in move.move_line_ids:
#                     move_line.quantity = move_line.reserved_uom_qty
#
#         _logger.info("Set quantities done on move lines")
#
#         # Validate the picking
#         try:
#             result = picking.button_validate()
#             _logger.info(f"Picking validation result: {result}")
#
#             # Handle backorder wizard if it appears
#             if isinstance(result, dict) and result.get('res_model') == 'stock.backorder.confirmation':
#                 backorder_wizard = self.env['stock.backorder.confirmation'].browse(result.get('res_id'))
#                 backorder_wizard.process_cancel_backorder()
#                 _logger.info("Processed backorder wizard")
#         except Exception as e:
#             _logger.error(f"Error validating picking: {str(e)}")
#             raise UserError(_(f"Error validating delivery order: {str(e)}"))
#
#         # Link picking to invoice
#         self.picking_id = picking.id
#         _logger.info(f"Successfully linked picking {picking.name} to invoice {self.name}")
#
#         # Show success message
#         message = _('Delivery order %s has been created and validated automatically.') % picking.name
#         self.message_post(body=message)
#
#         return picking
#
#     def action_view_delivery(self):
#         """Smart button to view related delivery order"""
#         self.ensure_one()
#         return {
#             'type': 'ir.actions.act_window',
#             'name': _('Delivery Order'),
#             'res_model': 'stock.picking',
#             'res_id': self.picking_id.id,
#             'view_mode': 'form',
#             'target': 'current',
#         }

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    picking_id = fields.Many2one('stock.picking', string='Delivery Order', readonly=True, copy=False)
    create_delivery = fields.Boolean(
        string='Create Delivery Order',
        default=False,
        help='Check this to automatically create delivery order on invoice validation'
    )

    def action_post(self):
        """Override the post method to create delivery order after invoice validation"""
        res = super(AccountMove, self).action_post()

        for invoice in self:
            # Only for customer invoices (out_invoice) with create_delivery flag
            if invoice.move_type == 'out_invoice' and invoice.create_delivery and not invoice.picking_id:
                try:
                    _logger.info(f"Creating delivery order for invoice: {invoice.name}")
                    invoice._create_delivery_from_invoice()
                except Exception as e:
                    _logger.error(f"Error creating delivery order for invoice {invoice.name}: {str(e)}")
                    raise UserError(_(f"Failed to create delivery order: {str(e)}"))

        return res

    def _create_delivery_from_invoice(self):
        """Create and validate delivery order from invoice"""
        self.ensure_one()

        _logger.info(f"Starting delivery creation for invoice: {self.name}")
        _logger.info(f"Total invoice lines: {len(self.invoice_line_ids)}")

        # Debug: Log all invoice lines
        for line in self.invoice_line_ids:
            _logger.info(f"Line: {line.name}, Product: {line.product_id.name if line.product_id else 'None'}, "
                         f"Product Type: {line.product_id.type if line.product_id else 'N/A'}, "
                         f"Quantity: {line.quantity}, Display Type: {line.display_type}")

        # Check if there are stockable products
        # In Odoo, 'product' type means storable/goods, 'consu' means consumable, 'service' means service
        # Exclude lines with display_type (section/note lines)
        stockable_lines = self.invoice_line_ids.filtered(
            lambda l: l.product_id and
                      not l.display_type and
                      l.product_id.type == 'product' and
                      l.quantity > 0
        )

        _logger.info(f"Stockable lines found: {len(stockable_lines)}")

        if not stockable_lines:
            _logger.error(f"No stockable products found in invoice {self.name}")
            error_msg = 'No stockable products found. Details:\n'
            for line in self.invoice_line_ids:
                if line.product_id:
                    error_msg += f"- {line.product_id.name}: Type={line.product_id.type}, Qty={line.quantity}, Display={line.display_type}\n"
            raise UserError(_(error_msg))

        _logger.info(f"Found {len(stockable_lines)} stockable lines")

        # Get warehouse
        warehouse = self.env['stock.warehouse'].search([
            ('company_id', '=', self.company_id.id)
        ], limit=1)

        if not warehouse:
            _logger.error(f"No warehouse found for company {self.company_id.name}")
            raise UserError(
                _('No warehouse found for company %s. Please create a warehouse first.') % self.company_id.name)

        _logger.info(f"Using warehouse: {warehouse.name}")

        # Get stock location
        location_id = warehouse.lot_stock_id.id

        # Get customer location
        customer_location = self.env.ref('stock.stock_location_customers', raise_if_not_found=False)
        if not customer_location:
            # Fallback: search for customer location
            customer_location = self.env['stock.location'].search([
                ('usage', '=', 'customer')
            ], limit=1)

        if not customer_location:
            raise UserError(_('Customer location not found. Please check your stock configuration.'))

        location_dest_id = customer_location.id

        # Create picking (delivery order)
        picking_type = warehouse.out_type_id

        if not picking_type:
            raise UserError(_('Delivery operation type not found in warehouse %s') % warehouse.name)

        _logger.info(f"Creating picking with type: {picking_type.name}")

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
        _logger.info(f"Created picking: {picking.name}")

        # Create stock moves for each invoice line
        moves_created = 0
        for line in stockable_lines:
            _logger.info(f"Creating move for product: {line.product_id.name}, qty: {line.quantity}")

            move_vals = {
                'name': line.product_id.name or '/',
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
            _logger.info(f"Created stock move: {move.name}")

        if moves_created == 0:
            picking.unlink()
            raise UserError(_('No stock moves could be created.'))

        _logger.info(f"Total moves created: {moves_created}")

        # Confirm the picking
        picking.action_confirm()
        _logger.info("Picking confirmed")

        # Check if picking is ready
        if picking.state != 'assigned':
            _logger.warning(f"Picking state is {picking.state}, attempting to force assign")
            picking.action_assign()

        # Auto-validate the picking (set quantities done)
        for move in picking.move_ids:
            for move_line in move.move_line_ids:
                move_line.quantity = move_line.reserved_uom_qty
            # If no move lines, create them
            if not move.move_line_ids:
                move._action_assign()
                for move_line in move.move_line_ids:
                    move_line.quantity = move_line.reserved_uom_qty

        _logger.info("Set quantities done on move lines")

        # Validate the picking
        try:
            result = picking.button_validate()
            _logger.info(f"Picking validation result: {result}")

            # Handle backorder wizard if it appears
            if isinstance(result, dict) and result.get('res_model') == 'stock.backorder.confirmation':
                backorder_wizard = self.env['stock.backorder.confirmation'].browse(result.get('res_id'))
                backorder_wizard.process_cancel_backorder()
                _logger.info("Processed backorder wizard")
        except Exception as e:
            _logger.error(f"Error validating picking: {str(e)}")
            raise UserError(_(f"Error validating delivery order: {str(e)}"))

        # Link picking to invoice
        self.picking_id = picking.id
        _logger.info(f"Successfully linked picking {picking.name} to invoice {self.name}")

        # Show success message
        message = _('Delivery order %s has been created and validated automatically.') % picking.name
        self.message_post(body=message)

        return picking

    def action_view_delivery(self):
        """Smart button to view related delivery order"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Delivery Order'),
            'res_model': 'stock.picking',
            'res_id': self.picking_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
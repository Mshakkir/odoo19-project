# # from odoo import models, fields, api, _
# # from odoo.exceptions import UserError
# # import logging
# #
# # _logger = logging.getLogger(__name__)
# #
# #
# # class AccountMove(models.Model):
# #     _inherit = 'account.move'
# #
# #     picking_id = fields.Many2one('stock.picking', string='Delivery Order', readonly=True, copy=False)
# #     create_delivery = fields.Boolean(
# #         string='Create Delivery Order',
# #         default=False,
# #         help='Check this to automatically create delivery order on invoice validation'
# #     )
# #     warehouse_id = fields.Many2one(
# #         'stock.warehouse',
# #         string='Warehouse',
# #         help='Select warehouse for stock reduction. If not set, default warehouse will be used.'
# #     )
# #
# #     def action_post(self):
# #         """Override the post method to create delivery order after invoice validation"""
# #         res = super(AccountMove, self).action_post()
# #
# #         for invoice in self:
# #             # Only for customer invoices (out_invoice) with create_delivery flag
# #             if invoice.move_type == 'out_invoice' and invoice.create_delivery and not invoice.picking_id:
# #                 try:
# #                     _logger.info(f"Creating delivery order for invoice: {invoice.name}")
# #                     invoice._create_delivery_from_invoice()
# #                 except Exception as e:
# #                     _logger.error(f"Error creating delivery order for invoice {invoice.name}: {str(e)}")
# #                     raise UserError(_(f"Failed to create delivery order: {str(e)}"))
# #
# #         return res
# #
# #     def _create_delivery_from_invoice(self):
# #         """Create and validate delivery order from invoice"""
# #         self.ensure_one()
# #
# #         _logger.info(f"Starting delivery creation for invoice: {self.name}")
# #         _logger.info(f"Total invoice lines: {len(self.invoice_line_ids)}")
# #
# #         # Debug: Log all invoice lines
# #         for line in self.invoice_line_ids:
# #             _logger.info(f"Line: {line.name}, Product: {line.product_id.name if line.product_id else 'None'}, "
# #                          f"Product Type: {line.product_id.type if line.product_id else 'N/A'}, "
# #                          f"Quantity: {line.quantity}, Display Type: {line.display_type}")
# #
# #         # Check for products that should create delivery orders
# #         # Accept ALL products except services
# #         # Note: display_type can be 'product', 'line_section', 'line_note', or False
# #         stockable_lines = []
# #         for line in self.invoice_line_ids:
# #             _logger.info(f"Checking line: Product={line.product_id.name if line.product_id else 'None'}, "
# #                          f"Type={line.product_id.type if line.product_id else 'N/A'}, "
# #                          f"Display_Type={line.display_type}, Qty={line.quantity}")
# #
# #             # Exclude section and note lines, but include 'product' display_type
# #             if (line.product_id and
# #                     line.product_id.type != 'service' and
# #                     line.quantity > 0 and
# #                     line.display_type not in ['line_section', 'line_note']):  # Allow 'product' and False
# #                 stockable_lines.append(line)
# #                 _logger.info(f"✓ Line accepted for delivery: {line.product_id.name}")
# #             else:
# #                 _logger.info(
# #                     f"✗ Line rejected - Service={line.product_id.type == 'service' if line.product_id else 'N/A'}, "
# #                     f"Display={line.display_type}")
# #
# #         _logger.info(f"Total products found for delivery: {len(stockable_lines)}")
# #
# #         if not stockable_lines:
# #             _logger.error(f"No products found for delivery in invoice {self.name}")
# #             error_msg = 'No products found for delivery creation. Details:\n'
# #             for line in self.invoice_line_ids:
# #                 if line.product_id:
# #                     error_msg += f"- {line.product_id.name}: Type={line.product_id.type}, Qty={line.quantity}, Display={line.display_type}\n"
# #             error_msg += '\nDebug: Check logs for detailed filtering information.'
# #             raise UserError(_(error_msg))
# #
# #         _logger.info(f"Found {len(stockable_lines)} stockable lines")
# #
# #         # Get warehouse
# #         warehouse = self.env['stock.warehouse'].search([
# #             ('company_id', '=', self.company_id.id)
# #         ], limit=1)
# #
# #         if not warehouse:
# #             _logger.error(f"No warehouse found for company {self.company_id.name}")
# #             raise UserError(
# #                 _('No warehouse found for company %s. Please create a warehouse first.') % self.company_id.name)
# #
# #         _logger.info(f"Using warehouse: {warehouse.name}")
# #
# #         # Get stock location
# #         location_id = warehouse.lot_stock_id.id
# #
# #         # Get customer location
# #         customer_location = self.env.ref('stock.stock_location_customers', raise_if_not_found=False)
# #         if not customer_location:
# #             # Fallback: search for customer location
# #             customer_location = self.env['stock.location'].search([
# #                 ('usage', '=', 'customer')
# #             ], limit=1)
# #
# #         if not customer_location:
# #             raise UserError(_('Customer location not found. Please check your stock configuration.'))
# #
# #         location_dest_id = customer_location.id
# #
# #         # Create picking (delivery order)
# #         picking_type = warehouse.out_type_id
# #
# #         if not picking_type:
# #             raise UserError(_('Delivery operation type not found in warehouse %s') % warehouse.name)
# #
# #         _logger.info(f"Creating picking with type: {picking_type.name}")
# #
# #         picking_vals = {
# #             'picking_type_id': picking_type.id,
# #             'partner_id': self.partner_id.id,
# #             'origin': self.name,
# #             'location_id': location_id,
# #             'location_dest_id': location_dest_id,
# #             'move_type': 'direct',
# #             'company_id': self.company_id.id,
# #         }
# #
# #         picking = self.env['stock.picking'].create(picking_vals)
# #         _logger.info(f"Created picking: {picking.name}")
# #
# #         # Create stock moves for each invoice line
# #         moves_created = 0
# #         for line in stockable_lines:
# #             _logger.info(f"Creating move for product: {line.product_id.name}, qty: {line.quantity}")
# #
# #             move_vals = {
# #                 'product_id': line.product_id.id,
# #                 'product_uom_qty': line.quantity,
# #                 'product_uom': line.product_uom_id.id,
# #                 'picking_id': picking.id,
# #                 'location_id': location_id,
# #                 'location_dest_id': location_dest_id,
# #                 'company_id': self.company_id.id,
# #                 'picking_type_id': picking_type.id,
# #             }
# #
# #             move = self.env['stock.move'].create(move_vals)
# #             moves_created += 1
# #             _logger.info(f"Created stock move: {move.id}")
# #
# #         if moves_created == 0:
# #             picking.unlink()
# #             raise UserError(_('No stock moves could be created.'))
# #
# #         _logger.info(f"Total moves created: {moves_created}")
# #
# #         # Confirm the picking
# #         picking.action_confirm()
# #         _logger.info("Picking confirmed")
# #
# #         # Check if picking is ready
# #         if picking.state != 'assigned':
# #             _logger.warning(f"Picking state is {picking.state}, attempting to force assign")
# #             picking.action_assign()
# #
# #         # Auto-validate the picking (set quantities done)
# #         for move in picking.move_ids:
# #             # Set the quantity done directly on the move
# #             move.quantity = move.product_uom_qty
# #
# #         _logger.info("Set quantities done on moves")
# #
# #         # Validate the picking
# #         try:
# #             result = picking.button_validate()
# #             _logger.info(f"Picking validation result: {result}")
# #
# #             # Handle backorder wizard if it appears
# #             if isinstance(result, dict) and result.get('res_model') == 'stock.backorder.confirmation':
# #                 backorder_wizard = self.env['stock.backorder.confirmation'].browse(result.get('res_id'))
# #                 backorder_wizard.process_cancel_backorder()
# #                 _logger.info("Processed backorder wizard")
# #         except Exception as e:
# #             _logger.error(f"Error validating picking: {str(e)}")
# #             raise UserError(_(f"Error validating delivery order: {str(e)}"))
# #
# #         # Link picking to invoice
# #         self.picking_id = picking.id
# #         _logger.info(f"Successfully linked picking {picking.name} to invoice {self.name}")
# #
# #         # Show success message
# #         message = _('Delivery order %s has been created and validated automatically.') % picking.name
# #         self.message_post(body=message)
# #
# #         return picking
# #
# #     def action_view_delivery(self):
# #         """Smart button to view related delivery order"""
# #         self.ensure_one()
# #         return {
# #             'type': 'ir.actions.act_window',
# #             'name': _('Delivery Order'),
# #             'res_model': 'stock.picking',
# #             'res_id': self.picking_id.id,
# #             'view_mode': 'form',
# #             'target': 'current',
# #         }
#
# #the stock reduce is successfully done use of below code
# # from odoo import models, fields, api, _
# # from odoo.exceptions import UserError
# # import logging
# #
# # _logger = logging.getLogger(__name__)
# #
# #
# # class AccountMove(models.Model):
# #     _inherit = 'account.move'
# #
# #     picking_id = fields.Many2one('stock.picking', string='Delivery Order', readonly=True, copy=False)
# #     create_delivery = fields.Boolean(
# #         string='Create Delivery Order',
# #         default=False,
# #         help='Check this to automatically create delivery order on invoice validation'
# #     )
# #     warehouse_id = fields.Many2one(
# #         'stock.warehouse',
# #         string='Warehouse',
# #         help='Select warehouse for stock reduction. If not set, default warehouse will be used.'
# #     )
# #
# #     def action_post(self):
# #         """Override the post method to create delivery order after invoice validation"""
# #         res = super(AccountMove, self).action_post()
# #
# #         for invoice in self:
# #             # Only for customer invoices (out_invoice) with create_delivery flag
# #             if invoice.move_type == 'out_invoice' and invoice.create_delivery and not invoice.picking_id:
# #                 try:
# #                     _logger.info(f"Creating delivery order for invoice: {invoice.name}")
# #                     invoice._create_delivery_from_invoice()
# #                 except Exception as e:
# #                     _logger.error(f"Error creating delivery order for invoice {invoice.name}: {str(e)}")
# #                     raise UserError(_(f"Failed to create delivery order: {str(e)}"))
# #
# #         return res
# #
# #     def _create_delivery_from_invoice(self):
# #         """Create and validate delivery order from invoice"""
# #         self.ensure_one()
# #
# #         _logger.info(f"Starting delivery creation for invoice: {self.name}")
# #         _logger.info(f"Total invoice lines: {len(self.invoice_line_ids)}")
# #
# #         # Debug: Log all invoice lines
# #         for line in self.invoice_line_ids:
# #             _logger.info(f"Line: {line.name}, Product: {line.product_id.name if line.product_id else 'None'}, "
# #                          f"Product Type: {line.product_id.type if line.product_id else 'N/A'}, "
# #                          f"Quantity: {line.quantity}, Display Type: {line.display_type}")
# #
# #         # Check for products that should create delivery orders
# #         stockable_lines = []
# #         for line in self.invoice_line_ids:
# #             _logger.info(f"Checking line: Product={line.product_id.name if line.product_id else 'None'}, "
# #                          f"Type={line.product_id.type if line.product_id else 'N/A'}, "
# #                          f"Display_Type={line.display_type}, Qty={line.quantity}")
# #
# #             # Exclude section and note lines, but include 'product' display_type
# #             if (line.product_id and
# #                     line.product_id.type != 'service' and
# #                     line.quantity > 0 and
# #                     line.display_type not in ['line_section', 'line_note']):
# #                 stockable_lines.append(line)
# #                 _logger.info(f"✓ Line accepted for delivery: {line.product_id.name}")
# #             else:
# #                 _logger.info(
# #                     f"✗ Line rejected - Service={line.product_id.type == 'service' if line.product_id else 'N/A'}, "
# #                     f"Display={line.display_type}")
# #
# #         _logger.info(f"Total products found for delivery: {len(stockable_lines)}")
# #
# #         if not stockable_lines:
# #             _logger.error(f"No products found for delivery in invoice {self.name}")
# #             error_msg = 'No products found for delivery creation. Details:\n'
# #             for line in self.invoice_line_ids:
# #                 if line.product_id:
# #                     error_msg += f"- {line.product_id.name}: Type={line.product_id.type}, Qty={line.quantity}, Display={line.display_type}\n"
# #             error_msg += '\nDebug: Check logs for detailed filtering information.'
# #             raise UserError(_(error_msg))
# #
# #         _logger.info(f"Found {len(stockable_lines)} stockable lines")
# #
# #         # Get warehouse - USE THE SELECTED WAREHOUSE OR DEFAULT
# #         if self.warehouse_id:
# #             warehouse = self.warehouse_id
# #             _logger.info(f"Using user-selected warehouse: {warehouse.name}")
# #         else:
# #             # Try to get warehouse from analytic account if available
# #             warehouse = None
# #             if self.invoice_line_ids and self.invoice_line_ids[0].analytic_distribution:
# #                 # Get first analytic account ID from distribution
# #                 analytic_dict = self.invoice_line_ids[0].analytic_distribution
# #                 if analytic_dict:
# #                     analytic_id = int(list(analytic_dict.keys())[0])
# #                     analytic_account = self.env['account.analytic.account'].browse(analytic_id)
# #                     if analytic_account:
# #                         # Search for warehouse with matching name
# #                         warehouse = self.env['stock.warehouse'].search([
# #                             ('name', 'ilike', analytic_account.name),
# #                             ('company_id', '=', self.company_id.id)
# #                         ], limit=1)
# #                         if warehouse:
# #                             _logger.info(f"Found warehouse from analytic account: {warehouse.name}")
# #
# #             # Fallback to default warehouse
# #             if not warehouse:
# #                 warehouse = self.env['stock.warehouse'].search([
# #                     ('company_id', '=', self.company_id.id)
# #                 ], limit=1)
# #                 _logger.info(f"Using default warehouse: {warehouse.name}")
# #
# #         if not warehouse:
# #             _logger.error(f"No warehouse found for company {self.company_id.name}")
# #             raise UserError(
# #                 _('No warehouse found for company %s. Please create a warehouse first.') % self.company_id.name)
# #
# #         _logger.info(f"Final warehouse selection: {warehouse.name} (ID: {warehouse.id})")
# #
# #         # Get stock location FROM THE SELECTED WAREHOUSE
# #         location_id = warehouse.lot_stock_id.id
# #         _logger.info(f"Using stock location: {warehouse.lot_stock_id.name} (ID: {location_id})")
# #
# #         # Get customer location
# #         customer_location = self.env.ref('stock.stock_location_customers', raise_if_not_found=False)
# #         if not customer_location:
# #             # Fallback: search for customer location
# #             customer_location = self.env['stock.location'].search([
# #                 ('usage', '=', 'customer')
# #             ], limit=1)
# #
# #         if not customer_location:
# #             raise UserError(_('Customer location not found. Please check your stock configuration.'))
# #
# #         location_dest_id = customer_location.id
# #
# #         # Create picking (delivery order) FROM THE SELECTED WAREHOUSE
# #         picking_type = warehouse.out_type_id
# #
# #         if not picking_type:
# #             raise UserError(_('Delivery operation type not found in warehouse %s') % warehouse.name)
# #
# #         _logger.info(f"Creating picking with type: {picking_type.name}")
# #
# #         picking_vals = {
# #             'picking_type_id': picking_type.id,
# #             'partner_id': self.partner_id.id,
# #             'origin': self.name,
# #             'location_id': location_id,
# #             'location_dest_id': location_dest_id,
# #             'move_type': 'direct',
# #             'company_id': self.company_id.id,
# #         }
# #
# #         picking = self.env['stock.picking'].create(picking_vals)
# #         _logger.info(f"Created picking: {picking.name} from warehouse: {warehouse.name}")
# #
# #         # Create stock moves for each invoice line
# #         moves_created = 0
# #         for line in stockable_lines:
# #             _logger.info(
# #                 f"Creating move for product: {line.product_id.name}, qty: {line.quantity} from location: {warehouse.lot_stock_id.name}")
# #
# #             move_vals = {
# #                 'product_id': line.product_id.id,
# #                 'product_uom_qty': line.quantity,
# #                 'product_uom': line.product_uom_id.id,
# #                 'picking_id': picking.id,
# #                 'location_id': location_id,
# #                 'location_dest_id': location_dest_id,
# #                 'company_id': self.company_id.id,
# #                 'picking_type_id': picking_type.id,
# #             }
# #
# #             move = self.env['stock.move'].create(move_vals)
# #             moves_created += 1
# #             _logger.info(f"Created stock move: {move.id} - {line.product_id.name}")
# #
# #         if moves_created == 0:
# #             picking.unlink()
# #             raise UserError(_('No stock moves could be created.'))
# #
# #         _logger.info(f"Total moves created: {moves_created}")
# #
# #         # Confirm the picking
# #         picking.action_confirm()
# #         _logger.info("Picking confirmed")
# #
# #         # Check if picking is ready
# #         if picking.state != 'assigned':
# #             _logger.warning(f"Picking state is {picking.state}, attempting to force assign")
# #             picking.action_assign()
# #
# #         # Auto-validate the picking (set quantities done)
# #         for move in picking.move_ids:
# #             # Set the quantity done directly on the move
# #             move.quantity = move.product_uom_qty
# #
# #         _logger.info("Set quantities done on moves")
# #
# #         # Validate the picking
# #         try:
# #             result = picking.button_validate()
# #             _logger.info(f"Picking validation result: {result}")
# #
# #             # Handle backorder wizard if it appears
# #             if isinstance(result, dict) and result.get('res_model') == 'stock.backorder.confirmation':
# #                 backorder_wizard = self.env['stock.backorder.confirmation'].browse(result.get('res_id'))
# #                 backorder_wizard.process_cancel_backorder()
# #                 _logger.info("Processed backorder wizard")
# #         except Exception as e:
# #             _logger.error(f"Error validating picking: {str(e)}")
# #             raise UserError(_(f"Error validating delivery order: {str(e)}"))
# #
# #         # Link picking to invoice
# #         self.picking_id = picking.id
# #         _logger.info(f"Successfully linked picking {picking.name} to invoice {self.name}")
# #
# #         # Show success message
# #         message = _('Delivery order %s has been created and validated automatically from warehouse %s.') % (
# #             picking.name, warehouse.name)
# #         self.message_post(body=message)
# #
# #         return picking
# #
# #     def action_view_delivery(self):
# #         """Smart button to view related delivery order"""
# #         self.ensure_one()
# #         return {
# #             'type': 'ir.actions.act_window',
# #             'name': _('Delivery Order'),
# #             'res_model': 'stock.picking',
# #             'res_id': self.picking_id.id,
# #             'view_mode': 'form',
# #             'target': 'current',
# #         }
#
# #this is for check the automatic warehouse select
# # from odoo import models, fields, api, _
# # from odoo.exceptions import UserError
# # import logging
# #
# # _logger = logging.getLogger(__name__)
# #
# #
# # class AccountMove(models.Model):
# #     _inherit = 'account.move'
# #
# #     picking_id = fields.Many2one('stock.picking', string='Delivery Order', readonly=True, copy=False)
# #     create_delivery = fields.Boolean(
# #         string='Create Delivery Order',
# #         default=False,
# #         help='Check this to automatically create delivery order on invoice validation'
# #     )
# #     warehouse_id = fields.Many2one(
# #         'stock.warehouse',
# #         string='Warehouse',
# #         help='Select warehouse for stock reduction. If not set, default warehouse will be used.'
# #     )
# #
# #     @api.onchange('invoice_line_ids')
# #     def _onchange_invoice_lines_set_warehouse(self):
# #         """Auto-set warehouse based on analytic account from invoice lines"""
# #         if self.invoice_line_ids and not self.warehouse_id:
# #             for line in self.invoice_line_ids:
# #                 if line.analytic_distribution:
# #                     # Get first analytic account from distribution
# #                     analytic_dict = line.analytic_distribution
# #                     if analytic_dict:
# #                         try:
# #                             analytic_id = int(list(analytic_dict.keys())[0])
# #                             analytic_account = self.env['account.analytic.account'].browse(analytic_id)
# #                             if analytic_account:
# #                                 # Search for warehouse with matching name
# #                                 warehouse = self.env['stock.warehouse'].search([
# #                                     ('name', 'ilike', analytic_account.name),
# #                                     ('company_id', '=', self.company_id.id)
# #                                 ], limit=1)
# #                                 if warehouse:
# #                                     self.warehouse_id = warehouse
# #                                     _logger.info(
# #                                         f"Auto-set warehouse to {warehouse.name} from analytic account {analytic_account.name}")
# #                                     break
# #                         except Exception as e:
# #                             _logger.warning(f"Error auto-setting warehouse from analytic: {str(e)}")
# #                             pass
# #
# #     def action_post(self):
# #         """Override the post method to create delivery order after invoice validation"""
# #         res = super(AccountMove, self).action_post()
# #
# #         for invoice in self:
# #             # Only for customer invoices (out_invoice) with create_delivery flag
# #             if invoice.move_type == 'out_invoice' and invoice.create_delivery and not invoice.picking_id:
# #                 try:
# #                     _logger.info(f"Creating delivery order for invoice: {invoice.name}")
# #                     invoice._create_delivery_from_invoice()
# #                 except Exception as e:
# #                     _logger.error(f"Error creating delivery order for invoice {invoice.name}: {str(e)}")
# #                     raise UserError(_(f"Failed to create delivery order: {str(e)}"))
# #
# #         return res
# #
# #     def _create_delivery_from_invoice(self):
# #         """Create and validate delivery order from invoice"""
# #         self.ensure_one()
# #
# #         _logger.info(f"Starting delivery creation for invoice: {self.name}")
# #         _logger.info(f"Total invoice lines: {len(self.invoice_line_ids)}")
# #
# #         # Debug: Log all invoice lines
# #         for line in self.invoice_line_ids:
# #             _logger.info(f"Line: {line.name}, Product: {line.product_id.name if line.product_id else 'None'}, "
# #                          f"Product Type: {line.product_id.type if line.product_id else 'N/A'}, "
# #                          f"Quantity: {line.quantity}, Display Type: {line.display_type}")
# #
# #         # Check for products that should create delivery orders
# #         stockable_lines = []
# #         for line in self.invoice_line_ids:
# #             _logger.info(f"Checking line: Product={line.product_id.name if line.product_id else 'None'}, "
# #                          f"Type={line.product_id.type if line.product_id else 'N/A'}, "
# #                          f"Display_Type={line.display_type}, Qty={line.quantity}")
# #
# #             # Exclude section and note lines, but include 'product' display_type
# #             if (line.product_id and
# #                     line.product_id.type != 'service' and
# #                     line.quantity > 0 and
# #                     line.display_type not in ['line_section', 'line_note']):
# #                 stockable_lines.append(line)
# #                 _logger.info(f"✓ Line accepted for delivery: {line.product_id.name}")
# #             else:
# #                 _logger.info(
# #                     f"✗ Line rejected - Service={line.product_id.type == 'service' if line.product_id else 'N/A'}, "
# #                     f"Display={line.display_type}")
# #
# #         _logger.info(f"Total products found for delivery: {len(stockable_lines)}")
# #
# #         if not stockable_lines:
# #             _logger.error(f"No products found for delivery in invoice {self.name}")
# #             error_msg = 'No products found for delivery creation. Details:\n'
# #             for line in self.invoice_line_ids:
# #                 if line.product_id:
# #                     error_msg += f"- {line.product_id.name}: Type={line.product_id.type}, Qty={line.quantity}, Display={line.display_type}\n"
# #             error_msg += '\nDebug: Check logs for detailed filtering information.'
# #             raise UserError(_(error_msg))
# #
# #         _logger.info(f"Found {len(stockable_lines)} stockable lines")
# #
# #         # Get warehouse - USE THE SELECTED WAREHOUSE OR DEFAULT
# #         if self.warehouse_id:
# #             warehouse = self.warehouse_id
# #             _logger.info(f"Using user-selected warehouse: {warehouse.name}")
# #         else:
# #             # Try to get warehouse from analytic account if available
# #             warehouse = None
# #             if self.invoice_line_ids and self.invoice_line_ids[0].analytic_distribution:
# #                 # Get first analytic account ID from distribution
# #                 analytic_dict = self.invoice_line_ids[0].analytic_distribution
# #                 if analytic_dict:
# #                     analytic_id = int(list(analytic_dict.keys())[0])
# #                     analytic_account = self.env['account.analytic.account'].browse(analytic_id)
# #                     if analytic_account:
# #                         # Search for warehouse with matching name
# #                         warehouse = self.env['stock.warehouse'].search([
# #                             ('name', 'ilike', analytic_account.name),
# #                             ('company_id', '=', self.company_id.id)
# #                         ], limit=1)
# #                         if warehouse:
# #                             _logger.info(f"Found warehouse from analytic account: {warehouse.name}")
# #
# #             # Fallback to default warehouse
# #             if not warehouse:
# #                 warehouse = self.env['stock.warehouse'].search([
# #                     ('company_id', '=', self.company_id.id)
# #                 ], limit=1)
# #                 _logger.info(f"Using default warehouse: {warehouse.name}")
# #
# #         if not warehouse:
# #             _logger.error(f"No warehouse found for company {self.company_id.name}")
# #             raise UserError(
# #                 _('No warehouse found for company %s. Please create a warehouse first.') % self.company_id.name)
# #
# #         _logger.info(f"Final warehouse selection: {warehouse.name} (ID: {warehouse.id})")
# #
# #         # Get stock location FROM THE SELECTED WAREHOUSE
# #         location_id = warehouse.lot_stock_id.id
# #         _logger.info(f"Using stock location: {warehouse.lot_stock_id.name} (ID: {location_id})")
# #
# #         # Get customer location
# #         customer_location = self.env.ref('stock.stock_location_customers', raise_if_not_found=False)
# #         if not customer_location:
# #             # Fallback: search for customer location
# #             customer_location = self.env['stock.location'].search([
# #                 ('usage', '=', 'customer')
# #             ], limit=1)
# #
# #         if not customer_location:
# #             raise UserError(_('Customer location not found. Please check your stock configuration.'))
# #
# #         location_dest_id = customer_location.id
# #
# #         # Create picking (delivery order) FROM THE SELECTED WAREHOUSE
# #         picking_type = warehouse.out_type_id
# #
# #         if not picking_type:
# #             raise UserError(_('Delivery operation type not found in warehouse %s') % warehouse.name)
# #
# #         _logger.info(f"Creating picking with type: {picking_type.name}")
# #
# #         picking_vals = {
# #             'picking_type_id': picking_type.id,
# #             'partner_id': self.partner_id.id,
# #             'origin': self.name,
# #             'location_id': location_id,
# #             'location_dest_id': location_dest_id,
# #             'move_type': 'direct',
# #             'company_id': self.company_id.id,
# #         }
# #
# #         picking = self.env['stock.picking'].create(picking_vals)
# #         _logger.info(f"Created picking: {picking.name} from warehouse: {warehouse.name}")
# #
# #         # Create stock moves for each invoice line
# #         moves_created = 0
# #         for line in stockable_lines:
# #             _logger.info(
# #                 f"Creating move for product: {line.product_id.name}, qty: {line.quantity} from location: {warehouse.lot_stock_id.name}")
# #
# #             move_vals = {
# #                 'product_id': line.product_id.id,
# #                 'product_uom_qty': line.quantity,
# #                 'product_uom': line.product_uom_id.id,
# #                 'picking_id': picking.id,
# #                 'location_id': location_id,
# #                 'location_dest_id': location_dest_id,
# #                 'company_id': self.company_id.id,
# #                 'picking_type_id': picking_type.id,
# #             }
# #
# #             move = self.env['stock.move'].create(move_vals)
# #             moves_created += 1
# #             _logger.info(f"Created stock move: {move.id} - {line.product_id.name}")
# #
# #         if moves_created == 0:
# #             picking.unlink()
# #             raise UserError(_('No stock moves could be created.'))
# #
# #         _logger.info(f"Total moves created: {moves_created}")
# #
# #         # Confirm the picking
# #         picking.action_confirm()
# #         _logger.info("Picking confirmed")
# #
# #         # Check if picking is ready
# #         if picking.state != 'assigned':
# #             _logger.warning(f"Picking state is {picking.state}, attempting to force assign")
# #             picking.action_assign()
# #
# #         # Auto-validate the picking (set quantities done)
# #         for move in picking.move_ids:
# #             # Set the quantity done directly on the move
# #             move.quantity = move.product_uom_qty
# #
# #         _logger.info("Set quantities done on moves")
# #
# #         # Validate the picking
# #         try:
# #             result = picking.button_validate()
# #             _logger.info(f"Picking validation result: {result}")
# #
# #             # Handle backorder wizard if it appears
# #             if isinstance(result, dict) and result.get('res_model') == 'stock.backorder.confirmation':
# #                 backorder_wizard = self.env['stock.backorder.confirmation'].browse(result.get('res_id'))
# #                 backorder_wizard.process_cancel_backorder()
# #                 _logger.info("Processed backorder wizard")
# #         except Exception as e:
# #             _logger.error(f"Error validating picking: {str(e)}")
# #             raise UserError(_(f"Error validating delivery order: {str(e)}"))
# #
# #         # Link picking to invoice
# #         self.picking_id = picking.id
# #         _logger.info(f"Successfully linked picking {picking.name} to invoice {self.name}")
# #
# #         # Show success message
# #         message = _('Delivery order %s has been created and validated automatically from warehouse %s.') % (
# #             picking.name, warehouse.name)
# #         self.message_post(body=message)
# #
# #         return picking
# #
# #     def action_view_delivery(self):
# #         """Smart button to view related delivery order"""
# #         self.ensure_one()
# #         return {
# #             'type': 'ir.actions.act_window',
# #             'name': _('Delivery Order'),
# #             'res_model': 'stock.picking',
# #             'res_id': self.picking_id.id,
# #             'view_mode': 'form',
# #             'target': 'current',
# #         }
#
# # -*- coding: utf-8 -*-
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
#         """Override to handle invoices, credit notes, and stock movements"""
#         res = super(AccountMove, self).action_post()
#
#         for invoice in self:
#             # REGULAR INVOICE - Create delivery and reduce stock
#             if invoice.move_type == 'out_invoice' and invoice.create_delivery and not invoice.picking_id:
#                 try:
#                     _logger.info(f"Creating delivery order for invoice: {invoice.name}")
#                     invoice._create_delivery_from_invoice()
#                 except Exception as e:
#                     _logger.error(f"Error creating delivery order for invoice {invoice.name}: {str(e)}")
#                     raise UserError(_(f"Failed to create delivery order: {str(e)}"))
#
#             # CREDIT NOTE/REFUND - Create return and add stock back
#             elif invoice.move_type == 'out_refund' and invoice.create_delivery and not invoice.picking_id:
#                 try:
#                     _logger.info(f"Creating stock return for credit note: {invoice.name}")
#                     invoice._create_return_from_refund()
#                 except Exception as e:
#                     _logger.error(f"Error creating return for credit note {invoice.name}: {str(e)}")
#                     raise UserError(_(f"Failed to create stock return: {str(e)}"))
#
#         return res
#
#     def button_cancel(self):
#         """
#         PRIORITY 1: Invoice Cancellation Handler
#         Override cancel to properly handle delivery orders and prevent stock inconsistencies
#         """
#         for invoice in self:
#             if invoice.picking_id:
#                 if invoice.picking_id.state == 'done':
#                     # Stock already moved - CANNOT auto-reverse
#                     raise UserError(_(
#                         "⚠️ CANNOT CANCEL INVOICE\n\n"
#                         "Invoice: %s\n"
#                         "Delivery Order: %s is already VALIDATED\n"
#                         "Stock has been reduced from warehouse!\n\n"
#                         "═══════════════════════════════\n"
#                         "To cancel this invoice properly:\n"
#                         "═══════════════════════════════\n\n"
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
#                     # Delivery exists but NOT validated yet - safe to cancel
#                     picking_name = invoice.picking_id.name
#                     _logger.info(f"Cancelling unvalidated delivery {picking_name} for invoice {invoice.name}")
#
#                     try:
#                         invoice.picking_id.action_cancel()
#                         invoice.picking_id.unlink()
#                         invoice.picking_id = False
#
#                         # Log the cancellation
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
#         _logger.info(f"Starting delivery creation for invoice: {self.name}")
#
#         # Filter stockable products
#         stockable_lines = []
#         for line in self.invoice_line_ids:
#             if (line.product_id and
#                     line.product_id.type != 'service' and
#                     line.quantity > 0 and
#                     line.display_type not in ['line_section', 'line_note']):
#                 stockable_lines.append(line)
#                 _logger.info(f"✓ Line accepted: {line.product_id.name}")
#
#         if not stockable_lines:
#             error_msg = 'No stockable products found for delivery creation.\n\nProducts found:\n'
#             for line in self.invoice_line_ids:
#                 if line.product_id:
#                     error_msg += f"- {line.product_id.name}: Type={line.product_id.type}\n"
#             raise UserError(_(error_msg))
#
#         # Get warehouse
#         if self.warehouse_id:
#             warehouse = self.warehouse_id
#         else:
#             warehouse = None
#             if self.invoice_line_ids and self.invoice_line_ids[0].analytic_distribution:
#                 analytic_dict = self.invoice_line_ids[0].analytic_distribution
#                 if analytic_dict:
#                     analytic_id = int(list(analytic_dict.keys())[0])
#                     analytic_account = self.env['account.analytic.account'].browse(analytic_id)
#                     if analytic_account:
#                         warehouse = self.env['stock.warehouse'].search([
#                             ('name', 'ilike', analytic_account.name),
#                             ('company_id', '=', self.company_id.id)
#                         ], limit=1)
#
#             if not warehouse:
#                 warehouse = self.env['stock.warehouse'].search([
#                     ('company_id', '=', self.company_id.id)
#                 ], limit=1)
#
#         if not warehouse:
#             raise UserError(_('No warehouse found for company %s') % self.company_id.name)
#
#         location_id = warehouse.lot_stock_id.id
#
#         # ═══════════════════════════════════════════════════════════
#         # PRIORITY 3: NEGATIVE STOCK WARNING - CHECK BEFORE CREATING
#         # ═══════════════════════════════════════════════════════════
#         stock_warnings = []
#         is_stock_manager = self.env.user.has_group('stock.group_stock_manager')
#
#         for line in stockable_lines:
#             # Get available quantity at warehouse location
#             available_qty = line.product_id.with_context(
#                 location=location_id
#             ).qty_available
#
#             if available_qty < line.quantity:
#                 shortage = line.quantity - available_qty
#                 warning_msg = _(
#                     "⚠️ LOW STOCK ALERT\n"
#                     "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
#                     "Product: %s\n"
#                     "Available Stock: %.2f %s\n"
#                     "Requested Quantity: %.2f %s\n"
#                     "Shortage: %.2f %s\n"
#                     "Warehouse: %s\n"
#                     "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
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
#         # Handle stock warnings
#         if stock_warnings:
#             if not is_stock_manager:
#                 # BLOCK regular users from creating negative stock
#                 error_messages = "\n\n".join([w['message'] for w in stock_warnings])
#                 raise UserError(_(
#                     "%s\n\n"
#                     "❌ INSUFFICIENT STOCK\n"
#                     "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
#                     "You don't have permission to create deliveries with insufficient stock.\n\n"
#                     "Please contact your Inventory Manager or:\n"
#                     "• Reduce invoice quantities\n"
#                     "• Request stock replenishment\n"
#                     "• Check stock in other warehouses"
#                 ) % error_messages)
#             else:
#                 # WARN managers but allow to proceed
#                 warning_summary = "⚠️ NEGATIVE STOCK WARNING - Manager Override\n\n"
#                 for w in stock_warnings:
#                     warning_summary += f"• {w['product']}: Short by {w['shortage']:.2f}\n"
#
#                 self.message_post(
#                     body=warning_summary,
#                     message_type='notification',
#                     subtype_xmlid='mail.mt_note'
#                 )
#                 _logger.warning(f"Negative stock allowed by manager for invoice {self.name}: {warning_summary}")
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
#         _logger.info(f"Created picking: {picking.name} from warehouse: {warehouse.name}")
#
#         # Create stock moves
#         moves_created = 0
#         for line in stockable_lines:
#             move_vals = {
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
#             _logger.info(f"Created stock move: {move.id} - {line.product_id.name}")
#
#         if moves_created == 0:
#             picking.unlink()
#             raise UserError(_('No stock moves could be created'))
#
#         # Confirm and validate picking
#         picking.action_confirm()
#
#         if picking.state != 'assigned':
#             picking.action_assign()
#
#         # Set quantities done
#         for move in picking.move_ids:
#             move.quantity = move.product_uom_qty
#
#         # Validate picking
#         try:
#             result = picking.button_validate()
#
#             if isinstance(result, dict) and result.get('res_model') == 'stock.backorder.confirmation':
#                 backorder_wizard = self.env['stock.backorder.confirmation'].browse(result.get('res_id'))
#                 backorder_wizard.process_cancel_backorder()
#         except Exception as e:
#             _logger.error(f"Error validating picking: {str(e)}")
#             raise UserError(_(f"Error validating delivery order: {str(e)}"))
#
#         # Link picking to invoice
#         self.picking_id = picking.id
#         _logger.info(f"Successfully linked picking {picking.name} to invoice {self.name}")
#
#         # Success message
#         message = _('✅ Delivery order %s created and validated from warehouse %s') % (
#             picking.name, warehouse.name)
#         self.message_post(body=message)
#
#         return picking
#
#     def _create_return_from_refund(self):
#         """
#         PRIORITY 2: Credit Note Handler - Create stock return for refunds
#         Returns products back to warehouse inventory
#         """
#         self.ensure_one()
#
#         _logger.info(f"Starting return creation for credit note: {self.name}")
#
#         # Filter stockable products
#         stockable_lines = []
#         for line in self.invoice_line_ids:
#             if (line.product_id and
#                     line.product_id.type != 'service' and
#                     line.quantity > 0 and
#                     line.display_type not in ['line_section', 'line_note']):
#                 stockable_lines.append(line)
#
#         if not stockable_lines:
#             raise UserError(_('No stockable products found for return creation'))
#
#         # Get warehouse
#         if self.warehouse_id:
#             warehouse = self.warehouse_id
#         else:
#             warehouse = None
#             if self.invoice_line_ids and self.invoice_line_ids[0].analytic_distribution:
#                 analytic_dict = self.invoice_line_ids[0].analytic_distribution
#                 if analytic_dict:
#                     analytic_id = int(list(analytic_dict.keys())[0])
#                     analytic_account = self.env['account.analytic.account'].browse(analytic_id)
#                     if analytic_account:
#                         warehouse = self.env['stock.warehouse'].search([
#                             ('name', 'ilike', analytic_account.name),
#                             ('company_id', '=', self.company_id.id)
#                         ], limit=1)
#
#             if not warehouse:
#                 warehouse = self.env['stock.warehouse'].search([
#                     ('company_id', '=', self.company_id.id)
#                 ], limit=1)
#
#         if not warehouse:
#             raise UserError(_('No warehouse found for company %s') % self.company_id.name)
#
#         # For returns: Customer location → Warehouse
#         location_dest_id = warehouse.lot_stock_id.id
#
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
#
#         # Use incoming picking type for returns
#         picking_type = warehouse.in_type_id
#
#         if not picking_type:
#             raise UserError(_('Receipt operation type not found in warehouse %s') % warehouse.name)
#
#         # Create return picking
#         picking_vals = {
#             'picking_type_id': picking_type.id,
#             'partner_id': self.partner_id.id,
#             'origin': self.name + ' (Return)',
#             'location_id': location_id,
#             'location_dest_id': location_dest_id,
#             'move_type': 'direct',
#             'company_id': self.company_id.id,
#         }
#
#         picking = self.env['stock.picking'].create(picking_vals)
#         _logger.info(f"Created return picking: {picking.name} for credit note {self.name}")
#
#         # Create stock moves
#         moves_created = 0
#         for line in stockable_lines:
#             move_vals = {
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
#
#         if moves_created == 0:
#             picking.unlink()
#             raise UserError(_('No stock moves could be created for return'))
#
#         # Confirm and validate
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
#             _logger.error(f"Error validating return: {str(e)}")
#             raise UserError(_(f"Error validating return: {str(e)}"))
#
#         # Link return to credit note
#         self.picking_id = picking.id
#
#         message = _('✅ Stock return %s created and validated. Products returned to warehouse %s') % (
#             picking.name, warehouse.name)
#         self.message_post(body=message)
#
#         return picking
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
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        help='Select warehouse for stock reduction. If not set, default warehouse will be used.'
    )

    @api.onchange('invoice_line_ids')
    def _onchange_invoice_lines_set_warehouse(self):
        """Auto-set warehouse based on analytic account from invoice lines"""
        # ONLY for customer invoices/credit notes
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
                                    _logger.info(
                                        f"Auto-set warehouse to {warehouse.name} from analytic account {analytic_account.name}")
                                    break
                        except Exception as e:
                            _logger.warning(f"Error auto-setting warehouse from analytic: {str(e)}")
                            pass

    def action_post(self):
        """Override to handle CUSTOMER invoices and credit notes ONLY"""
        res = super(AccountMove, self).action_post()

        for invoice in self:
            _logger.info(f"🟢 INVOICE MODULE - Processing: {invoice.name}, Type: {invoice.move_type}")

            # ═══════════════════════════════════════════════════════════════
            # CRITICAL: ONLY HANDLE CUSTOMER TRANSACTIONS (out_invoice, out_refund)
            # Let direct_purchase_with_stock handle vendor transactions (in_invoice, in_refund)
            # ═══════════════════════════════════════════════════════════════

            # CUSTOMER INVOICE - Create delivery and reduce stock
            if invoice.move_type == 'out_invoice' and invoice.create_delivery and not invoice.picking_id:
                try:
                    _logger.info(f"🟢 INVOICE: Creating DELIVERY for customer invoice: {invoice.name}")
                    invoice._create_delivery_from_invoice()
                except Exception as e:
                    _logger.error(f"Error creating delivery order for invoice {invoice.name}: {str(e)}")
                    raise UserError(_(f"Failed to create delivery order: {str(e)}"))

            # CUSTOMER CREDIT NOTE - Create return and add stock back
            elif invoice.move_type == 'out_refund' and invoice.create_delivery and not invoice.picking_id:
                try:
                    _logger.info(f"🟢 INVOICE: Creating CUSTOMER RETURN for credit note: {invoice.name}")
                    invoice._create_customer_return_from_refund()
                except Exception as e:
                    _logger.error(f"Error creating return for credit note {invoice.name}: {str(e)}")
                    raise UserError(_(f"Failed to create stock return: {str(e)}"))

        return res

    def button_cancel(self):
        """Override cancel to properly handle delivery orders"""
        for invoice in self:
            # ONLY handle customer transactions
            if invoice.move_type not in ['out_invoice', 'out_refund']:
                continue

            if invoice.picking_id:
                if invoice.picking_id.state == 'done':
                    raise UserError(_(
                        "⚠️ CANNOT CANCEL INVOICE\n\n"
                        "Invoice: %s\n"
                        "Delivery Order: %s is already VALIDATED\n"
                        "Stock has been reduced from warehouse!\n\n"
                        "╔═══════════════════════════════╗\n"
                        "To cancel this invoice properly:\n"
                        "╚═══════════════════════════════╝\n\n"
                        "Option 1: CREATE A CREDIT NOTE\n"
                        "   • Go to invoice and click 'Add Credit Note'\n"
                        "   • This will reverse the accounting entry\n"
                        "   • If you want stock back, check 'Create Delivery Order'\n\n"
                        "Option 2: MANUAL RETURN (Inventory)\n"
                        "   • Go to Inventory → Returns\n"
                        "   • Create return for delivery %s\n"
                        "   • Then you can cancel this invoice\n\n"
                        "This protection prevents inventory discrepancies."
                    ) % (invoice.name, invoice.picking_id.name, invoice.picking_id.name))

                elif invoice.picking_id.state in ['confirmed', 'assigned', 'waiting']:
                    picking_name = invoice.picking_id.name
                    _logger.info(f"Cancelling unvalidated delivery {picking_name} for invoice {invoice.name}")

                    try:
                        invoice.picking_id.action_cancel()
                        invoice.picking_id.unlink()
                        invoice.picking_id = False

                        self.message_post(body=_(
                            "✅ Delivery order %s was cancelled and removed successfully.\n"
                            "No stock movement occurred."
                        ) % picking_name)

                        _logger.info(f"Successfully cancelled and removed delivery {picking_name}")
                    except Exception as e:
                        _logger.error(f"Error cancelling delivery {picking_name}: {str(e)}")
                        raise UserError(_(
                            "Error cancelling delivery order %s: %s"
                        ) % (picking_name, str(e)))

        return super(AccountMove, self).button_cancel()

    def _create_delivery_from_invoice(self):
        """Create and validate delivery order from invoice with stock checking"""
        self.ensure_one()

        _logger.info(f"🟢 INVOICE: Starting delivery creation for invoice: {self.name}")

        # Filter stockable products
        stockable_lines = []
        for line in self.invoice_line_ids:
            if (line.product_id and
                    line.product_id.type != 'service' and
                    line.quantity > 0 and
                    line.display_type not in ['line_section', 'line_note']):
                stockable_lines.append(line)
                _logger.info(f"   ✓ Line accepted: {line.product_id.name}")

        if not stockable_lines:
            error_msg = 'No stockable products found for delivery creation.\n\nProducts found:\n'
            for line in self.invoice_line_ids:
                if line.product_id:
                    error_msg += f"- {line.product_id.name}: Type={line.product_id.type}\n"
            raise UserError(_(error_msg))

        # Get warehouse
        warehouse = self._get_warehouse()

        location_id = warehouse.lot_stock_id.id

        # ═══════════════════════════════════════════════════════════════
        # STOCK AVAILABILITY CHECK
        # ═══════════════════════════════════════════════════════════════
        stock_warnings = []
        is_stock_manager = self.env.user.has_group('stock.group_stock_manager')

        for line in stockable_lines:
            available_qty = line.product_id.with_context(
                location=location_id
            ).qty_available

            if available_qty < line.quantity:
                shortage = line.quantity - available_qty
                warning_msg = _(
                    "⚠️ LOW STOCK ALERT\n"
                    "┌───────────────────────────────┐\n"
                    "Product: %s\n"
                    "Available Stock: %.2f %s\n"
                    "Requested Quantity: %.2f %s\n"
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

        if stock_warnings:
            if not is_stock_manager:
                error_messages = "\n\n".join([w['message'] for w in stock_warnings])
                raise UserError(_(
                    "%s\n\n"
                    "❌ INSUFFICIENT STOCK\n"
                    "You don't have permission to create deliveries with insufficient stock."
                ) % error_messages)
            else:
                warning_summary = "⚠️ NEGATIVE STOCK WARNING - Manager Override\n\n"
                for w in stock_warnings:
                    warning_summary += f"• {w['product']}: Short by {w['shortage']:.2f}\n"

                self.message_post(
                    body=warning_summary,
                    message_type='notification',
                    subtype_xmlid='mail.mt_note'
                )
                _logger.warning(f"Negative stock allowed by manager for invoice {self.name}")

        # Get customer location
        customer_location = self.env.ref('stock.stock_location_customers', raise_if_not_found=False)
        if not customer_location:
            customer_location = self.env['stock.location'].search([
                ('usage', '=', 'customer')
            ], limit=1)

        if not customer_location:
            raise UserError(_('Customer location not found'))

        location_dest_id = customer_location.id

        _logger.info(f"   📦 FROM: {warehouse.lot_stock_id.complete_name} → TO: {customer_location.complete_name}")

        # Use OUTGOING picking type
        picking_type = warehouse.out_type_id

        if not picking_type:
            raise UserError(_('Delivery operation type not found in warehouse %s') % warehouse.name)

        # Create picking
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
        _logger.info(f"   Created picking: {picking.name} from warehouse: {warehouse.name}")

        # Create stock moves
        self._create_stock_moves(picking, stockable_lines, location_id, location_dest_id, picking_type)

        # Validate picking
        self._validate_picking(picking)

        # Link picking to invoice
        self.picking_id = picking.id
        _logger.info(f"   Successfully linked picking {picking.name} to invoice {self.name}")

        # Success message
        message = _('✅ Delivery order %s created and validated from warehouse %s') % (
            picking.name, warehouse.name)
        self.message_post(body=message)

        return picking

    def _create_customer_return_from_refund(self):
        """
        🟢 CUSTOMER RETURN: Receive goods FROM customer (ADDS stock to warehouse)

        Flow: Customers → Warehouse Stock
        This INCREASES inventory
        """
        self.ensure_one()

        _logger.info(f"🟢 INVOICE: Starting CUSTOMER return for credit note: {self.name}")

        # Filter stockable products
        stockable_lines = []
        for line in self.invoice_line_ids:
            if (line.product_id and
                    line.product_id.type != 'service' and
                    line.quantity > 0 and
                    line.display_type not in ['line_section', 'line_note']):
                stockable_lines.append(line)
                _logger.info(f"   ✓ Product: {line.product_id.name} - Qty: {line.quantity}")

        if not stockable_lines:
            raise UserError(_('No stockable products found for return creation'))

        # Get warehouse
        warehouse = self._get_warehouse()

        # ═══════════════════════════════════════════════════════════════
        # CRITICAL: CUSTOMER RETURN LOCATIONS
        # ═══════════════════════════════════════════════════════════════

        # Source: CUSTOMER location (where we're receiving stock FROM)
        customer_location = self.env.ref('stock.stock_location_customers', raise_if_not_found=False)
        if not customer_location:
            customer_location = self.env['stock.location'].search([
                ('usage', '=', 'customer')
            ], limit=1)

        if not customer_location:
            raise UserError(_('Customer location not found'))

        location_id = customer_location.id
        _logger.info(f"   📍 FROM (source): {customer_location.complete_name}")

        # Destination: OUR warehouse (where we're adding stock TO)
        location_dest_id = warehouse.lot_stock_id.id
        _logger.info(f"   📍 TO (destination): {warehouse.lot_stock_id.complete_name}")

        # Use INCOMING picking type for customer returns (goods entering warehouse)
        picking_type = warehouse.in_type_id

        if not picking_type:
            raise UserError(_('Receipt operation type not found in warehouse %s') % warehouse.name)

        _logger.info(f"   📦 Picking type: {picking_type.name} (code: {picking_type.code})")
        _logger.info(f"   🟢 This will ADD stock to warehouse")

        # Create return picking
        picking_vals = {
            'picking_type_id': picking_type.id,
            'partner_id': self.partner_id.id,
            'origin': self.name + ' (Customer Return)',
            'location_id': location_id,  # FROM customer
            'location_dest_id': location_dest_id,  # TO warehouse
            'move_type': 'direct',
            'company_id': self.company_id.id,
        }

        picking = self.env['stock.picking'].create(picking_vals)
        _logger.info(f"   🟢 Created CUSTOMER RETURN picking: {picking.name}")

        # Create stock moves
        self._create_stock_moves(picking, stockable_lines, location_id, location_dest_id, picking_type)

        # Validate picking
        self._validate_picking(picking)

        # Link return to credit note
        self.picking_id = picking.id

        message = _('✅ Customer Return %s created - Products returned FROM customer TO warehouse\n'
                    'Warehouse: %s\n'
                    'Stock INCREASED by return') % (picking.name, warehouse.name)
        self.message_post(body=message)

        _logger.info(f"   🟢 CUSTOMER RETURN completed - Stock ADDED to {warehouse.name}")
        return picking

    def _get_warehouse(self):
        """Get warehouse for stock operations"""
        if self.warehouse_id:
            return self.warehouse_id

        # Try to get from analytic account
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

        return warehouse

    def _create_stock_moves(self, picking, stockable_lines, location_id, location_dest_id, picking_type):
        """Create stock moves for picking"""
        moves_created = 0
        for line in stockable_lines:
            move_vals = {
                'name': f'{picking.origin}: {line.product_id.name}',
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
            _logger.info(f"   ✓ Created move: {line.product_id.name} - Qty: {line.quantity}")

        if moves_created == 0:
            picking.unlink()
            raise UserError(_('No stock moves could be created'))

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
        """Smart button to view related delivery order or return"""
        self.ensure_one()

        if not self.picking_id or not self.picking_id.exists():
            raise UserError(_('No delivery order found or it has been deleted'))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Delivery Order'),
            'res_model': 'stock.picking',
            'res_id': self.picking_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
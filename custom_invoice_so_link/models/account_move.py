# # from odoo import models, fields, api
# #
# #
# # class AccountMove(models.Model):
# #     _inherit = 'account.move'
# #
# #     # Field to select sales order
# #     sale_order_id = fields.Many2one(
# #         'sale.order',
# #         string='Sales Order',
# #         help="Select a sales order to create invoice from"
# #     )
# #
# #     # Field to show available sales orders for the customer
# #     available_sale_order_ids = fields.Many2many(
# #         'sale.order',
# #         compute='_compute_available_sale_orders',
# #         string='Available Sales Orders'
# #     )
# #
# #     # Field to display related delivery notes
# #     delivery_note_ids = fields.Many2many(
# #         'stock.picking',
# #         string='Delivery Notes',
# #         compute='_compute_delivery_notes',
# #         help="Delivery notes related to this customer"
# #     )
# #
# #     @api.depends('partner_id')
# #     def _compute_available_sale_orders(self):
# #         """Compute available sales orders for the selected customer"""
# #         for record in self:
# #             if record.partner_id and record.move_type in ['out_invoice', 'out_refund']:
# #                 # Find sales orders for this customer that can be invoiced
# #                 orders = self.env['sale.order'].search([
# #                     ('partner_id', '=', record.partner_id.id),
# #                     ('state', 'in', ['sale', 'done']),
# #                     ('invoice_status', 'in', ['to invoice', 'invoiced'])
# #                 ])
# #                 record.available_sale_order_ids = orders
# #             else:
# #                 record.available_sale_order_ids = False
# #
# #     @api.depends('partner_id')
# #     def _compute_delivery_notes(self):
# #         """Compute delivery notes for the selected customer"""
# #         for record in self:
# #             if record.partner_id:
# #                 # Find deliveries for this customer
# #                 deliveries = self.env['stock.picking'].search([
# #                     ('partner_id', '=', record.partner_id.id),
# #                     ('picking_type_code', '=', 'outgoing'),
# #                     ('state', '=', 'done')
# #                 ], limit=20)  # Limit to recent 20
# #                 record.delivery_note_ids = deliveries
# #             else:
# #                 record.delivery_note_ids = False
# #
# #     @api.onchange('partner_id')
# #     def _onchange_partner_id_clear_so(self):
# #         """Clear sales order when customer changes"""
# #         if self.partner_id:
# #             self.sale_order_id = False
# #         return {
# #             'domain': {
# #                 'sale_order_id': [
# #                     ('partner_id', '=', self.partner_id.id),
# #                     ('state', 'in', ['sale', 'done']),
# #                     ('invoice_status', 'in', ['to invoice', 'invoiced'])
# #                 ]
# #             }
# #         }
# #
# #     @api.onchange('sale_order_id')
# #     def _onchange_sale_order_id(self):
# #         """Populate invoice lines from selected sales order"""
# #         if self.sale_order_id and self.move_type in ['out_invoice', 'out_refund']:
# #             # Clear existing lines
# #             self.invoice_line_ids = [(5, 0, 0)]
# #
# #             # Create invoice lines from sales order lines
# #             invoice_lines = []
# #             for line in self.sale_order_id.order_line:
# #                 # Skip lines without products or display type lines
# #                 if not line.product_id or line.display_type:
# #                     continue
# #
# #                 # Only add lines that need to be invoiced
# #                 qty_to_invoice = line.product_uom_qty - line.qty_invoiced
# #
# #                 if qty_to_invoice > 0:
# #                     invoice_line_vals = {
# #                         'product_id': line.product_id.id,
# #                         'name': line.name,
# #                         'quantity': qty_to_invoice,
# #                         'price_unit': line.price_unit,
# #                         'tax_ids': [(6, 0, line.tax_ids.ids)],  # Changed from tax_id to tax_ids
# #                         'sale_line_ids': [(6, 0, [line.id])],
# #                     }
# #
# #                     # Set account if available
# #                     account = line.product_id.property_account_income_id or \
# #                               line.product_id.categ_id.property_account_income_categ_id
# #                     if account:
# #                         invoice_line_vals['account_id'] = account.id
# #
# #                     invoice_lines.append((0, 0, invoice_line_vals))
# #
# #             if invoice_lines:
# #                 self.invoice_line_ids = invoice_lines
# #
# #             # Set other invoice fields from SO
# #             self.invoice_origin = self.sale_order_id.name
# #             self.payment_reference = self.sale_order_id.name
# #
# #             # Set fiscal position if available
# #             if self.sale_order_id.fiscal_position_id:
# #                 self.fiscal_position_id = self.sale_order_id.fiscal_position_id
#
# from odoo import models, fields, api
#
#
# class AccountMove(models.Model):
#     _inherit = 'account.move'
#
#     # Field to select sales order
#     sale_order_id = fields.Many2one(
#         'sale.order',
#         string='Sales Order',
#         help="Select a sales order to create invoice from"
#     )
#
#     # Field to show available sales orders for the customer
#     available_sale_order_ids = fields.Many2many(
#         'sale.order',
#         compute='_compute_available_sale_orders',
#         string='Available Sales Orders'
#     )
#
#     # Field to display related delivery notes
#     delivery_note_ids = fields.Many2many(
#         'stock.picking',
#         string='Delivery Notes',
#         compute='_compute_delivery_notes',
#         help="Delivery notes related to this customer"
#     )
#
#     @api.depends('partner_id')
#     def _compute_available_sale_orders(self):
#         """Compute available sales orders for the selected customer"""
#         for record in self:
#             if record.partner_id and record.move_type in ['out_invoice', 'out_refund']:
#                 # Find sales orders for this customer that can be invoiced
#                 orders = self.env['sale.order'].search([
#                     ('partner_id', '=', record.partner_id.id),
#                     ('state', 'in', ['sale', 'done']),
#                     ('invoice_status', 'in', ['to invoice', 'invoiced'])
#                 ])
#                 record.available_sale_order_ids = orders
#             else:
#                 record.available_sale_order_ids = False
#
#     @api.depends('partner_id')
#     def _compute_delivery_notes(self):
#         """Compute delivery notes for the selected customer"""
#         for record in self:
#             if record.partner_id:
#                 # Find deliveries for this customer
#                 deliveries = self.env['stock.picking'].search([
#                     ('partner_id', '=', record.partner_id.id),
#                     ('picking_type_code', '=', 'outgoing'),
#                     ('state', '=', 'done')
#                 ], limit=20)  # Limit to recent 20
#                 record.delivery_note_ids = deliveries
#             else:
#                 record.delivery_note_ids = False
#
#     @api.onchange('partner_id')
#     def _onchange_partner_id_clear_so(self):
#         """Clear sales order when customer changes"""
#         if self.partner_id:
#             self.sale_order_id = False
#         return {
#             'domain': {
#                 'sale_order_id': [
#                     ('partner_id', '=', self.partner_id.id),
#                     ('state', 'in', ['sale', 'done']),
#                     ('invoice_status', 'in', ['to invoice', 'invoiced'])
#                 ]
#             }
#         }
#
#     @api.onchange('sale_order_id')
#     def _onchange_sale_order_id(self):
#         """Populate invoice lines from selected sales order"""
#         if self.sale_order_id and self.move_type in ['out_invoice', 'out_refund']:
#             # Clear existing lines
#             self.invoice_line_ids = [(5, 0, 0)]
#
#             # Create invoice lines from sales order lines
#             invoice_lines = []
#             for line in self.sale_order_id.order_line:
#                 # Skip lines without products or display type lines
#                 if not line.product_id or line.display_type:
#                     continue
#
#                 # Only add lines that need to be invoiced
#                 qty_to_invoice = line.product_uom_qty - line.qty_invoiced
#
#                 if qty_to_invoice > 0:
#                     invoice_line_vals = {
#                         'product_id': line.product_id.id,
#                         'name': line.name,
#                         'quantity': qty_to_invoice,
#                         'price_unit': line.price_unit,
#                         'tax_ids': [(6, 0, line.tax_ids.ids)],
#                         'sale_line_ids': [(6, 0, [line.id])],
#                     }
#
#                     # Set account if available
#                     account = line.product_id.property_account_income_id or \
#                               line.product_id.categ_id.property_account_income_categ_id
#                     if account:
#                         invoice_line_vals['account_id'] = account.id
#
#                     invoice_lines.append((0, 0, invoice_line_vals))
#
#             if invoice_lines:
#                 self.invoice_line_ids = invoice_lines
#
#             # Set other invoice fields from SO
#             self.invoice_origin = self.sale_order_id.name
#             self.payment_reference = self.sale_order_id.name
#
#             # Set PO Number (Customer Reference) from Sales Order
#             if hasattr(self.sale_order_id, 'client_order_ref') and self.sale_order_id.client_order_ref:
#                 # Check which field exists on invoice for PO Number
#                 if hasattr(self, 'ref'):
#                     self.ref = self.sale_order_id.client_order_ref
#                 elif hasattr(self, 'client_order_ref'):
#                     self.client_order_ref = self.sale_order_id.client_order_ref
#                 elif hasattr(self, 'po_number'):
#                     self.po_number = self.sale_order_id.client_order_ref
#
#             # Set AWB Number from Sales Order
#             if hasattr(self.sale_order_id, 'awb_number') and self.sale_order_id.awb_number:
#                 if hasattr(self, 'awb_number'):
#                     self.awb_number = self.sale_order_id.awb_number
#
#             # Set fiscal position if available
#             if self.sale_order_id.fiscal_position_id:
#                 self.fiscal_position_id = self.sale_order_id.fiscal_position_id
#
#             # Get delivery information from related picking
#             picking = self.env['stock.picking'].search([
#                 ('sale_id', '=', self.sale_order_id.id),
#                 ('picking_type_code', '=', 'outgoing'),
#                 ('state', '=', 'done')
#             ], limit=1, order='date_done desc')
#
#             if picking:
#                 # Set Delivery Note Number
#                 if hasattr(self, 'l10n_in_shipping_bill_number'):
#                     self.l10n_in_shipping_bill_number = picking.name
#                 elif hasattr(self, 'delivery_note_number'):
#                     self.delivery_note_number = picking.name

# from odoo import models, fields, api
#
#
# class AccountMove(models.Model):
#     _inherit = 'account.move'
#
#     # Field to select sales order
#     sale_order_id = fields.Many2one(
#         'sale.order',
#         string='Sales Order',
#         help="Select a sales order to create invoice from"
#     )
#
#     # Field to show available sales orders for the customer
#     available_sale_order_ids = fields.Many2many(
#         'sale.order',
#         compute='_compute_available_sale_orders',
#         string='Available Sales Orders'
#     )
#
#     # Field to display related delivery notes
#     delivery_note_ids = fields.Many2many(
#         'stock.picking',
#         string='Delivery Notes',
#         compute='_compute_delivery_notes',
#         help="Delivery notes related to this customer"
#     )
#
#     @api.depends('partner_id')
#     def _compute_available_sale_orders(self):
#         """Compute available sales orders for the selected customer"""
#         for record in self:
#             if record.partner_id and record.move_type in ['out_invoice', 'out_refund']:
#                 # Find sales orders for this customer that can be invoiced
#                 orders = self.env['sale.order'].search([
#                     ('partner_id', '=', record.partner_id.id),
#                     ('state', 'in', ['sale', 'done']),
#                     ('invoice_status', 'in', ['to invoice', 'invoiced'])
#                 ])
#                 record.available_sale_order_ids = orders
#             else:
#                 record.available_sale_order_ids = False
#
#     @api.depends('partner_id')
#     def _compute_delivery_notes(self):
#         """Compute delivery notes for the selected customer"""
#         for record in self:
#             if record.partner_id:
#                 # Find deliveries for this customer
#                 deliveries = self.env['stock.picking'].search([
#                     ('partner_id', '=', record.partner_id.id),
#                     ('picking_type_code', '=', 'outgoing'),
#                     ('state', '=', 'done')
#                 ], limit=20)  # Limit to recent 20
#                 record.delivery_note_ids = deliveries
#             else:
#                 record.delivery_note_ids = False
#
#     @api.onchange('partner_id')
#     def _onchange_partner_id_clear_so(self):
#         """Clear sales order when customer changes"""
#         if self.partner_id:
#             self.sale_order_id = False
#         return {
#             'domain': {
#                 'sale_order_id': [
#                     ('partner_id', '=', self.partner_id.id),
#                     ('state', 'in', ['sale', 'done']),
#                     ('invoice_status', 'in', ['to invoice', 'invoiced'])
#                 ]
#             }
#         }
#
#     @api.onchange('sale_order_id')
#     def _onchange_sale_order_id(self):
#         """Populate invoice lines from selected sales order"""
#         if self.sale_order_id and self.move_type in ['out_invoice', 'out_refund']:
#             # Clear existing lines
#             self.invoice_line_ids = [(5, 0, 0)]
#
#             # Create invoice lines from sales order lines
#             invoice_lines = []
#             for line in self.sale_order_id.order_line:
#                 # Skip lines without products or display type lines
#                 if not line.product_id or line.display_type:
#                     continue
#
#                 # Only add lines that need to be invoiced
#                 qty_to_invoice = line.product_uom_qty - line.qty_invoiced
#
#                 if qty_to_invoice > 0:
#                     invoice_line_vals = {
#                         'product_id': line.product_id.id,
#                         'name': line.name,
#                         'quantity': qty_to_invoice,
#                         'price_unit': line.price_unit,
#                         'tax_ids': [(6, 0, line.tax_ids.ids)],
#                         'sale_line_ids': [(6, 0, [line.id])],
#                     }
#
#                     # Set account if available
#                     account = line.product_id.property_account_income_id or \
#                               line.product_id.categ_id.property_account_income_categ_id
#                     if account:
#                         invoice_line_vals['account_id'] = account.id
#
#                     invoice_lines.append((0, 0, invoice_line_vals))
#
#             if invoice_lines:
#                 self.invoice_line_ids = invoice_lines
#
#             # Set other invoice fields from SO
#             self.invoice_origin = self.sale_order_id.name
#             self.payment_reference = self.sale_order_id.name
#
#             # Set PO Number and Customer Reference from Sales Order
#             if hasattr(self.sale_order_id, 'client_order_ref') and self.sale_order_id.client_order_ref:
#                 # Set PO Number field (client_order_ref) - shown on main form
#                 self.client_order_ref = self.sale_order_id.client_order_ref
#
#                 # Set Customer Reference field (ref) - shown in Other Info tab
#                 self.ref = self.sale_order_id.client_order_ref
#
#             # Set AWB Number from Sales Order
#             if hasattr(self.sale_order_id, 'awb_number') and self.sale_order_id.awb_number:
#                 if hasattr(self, 'awb_number'):
#                     self.awb_number = self.sale_order_id.awb_number
#
#             # Set fiscal position if available
#             if self.sale_order_id.fiscal_position_id:
#                 self.fiscal_position_id = self.sale_order_id.fiscal_position_id
#
#             # Get delivery information from related picking
#             picking = self.env['stock.picking'].search([
#                 ('sale_id', '=', self.sale_order_id.id),
#                 ('picking_type_code', '=', 'outgoing'),
#                 ('state', '=', 'done')
#             ], limit=1, order='date_done desc')
#
#             if picking:
#                 # Set Delivery Note Number
#                 if hasattr(self, 'l10n_in_shipping_bill_number'):
#                     self.l10n_in_shipping_bill_number = picking.name
#                 elif hasattr(self, 'delivery_note_number'):
#                     self.delivery_note_number = picking.name

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    # Field to select sales order
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sales Order',
        help="Select a sales order to create invoice from"
    )

    # Field to show available sales orders for the customer
    available_sale_order_ids = fields.Many2many(
        'sale.order',
        compute='_compute_available_sale_orders',
        string='Available Sales Orders'
    )

    # Field to display related delivery notes
    delivery_note_ids = fields.Many2many(
        'stock.picking',
        string='Delivery Notes',
        compute='_compute_delivery_notes',
        help="Delivery notes related to this customer"
    )

    @api.depends('partner_id')
    def _compute_available_sale_orders(self):
        """Compute available sales orders for the selected customer"""
        for record in self:
            if record.partner_id and record.move_type in ['out_invoice', 'out_refund']:
                # Find sales orders for this customer that can be invoiced
                orders = self.env['sale.order'].search([
                    ('partner_id', '=', record.partner_id.id),
                    ('state', 'in', ['sale', 'done']),
                    ('invoice_status', 'in', ['to invoice', 'invoiced'])
                ])
                record.available_sale_order_ids = orders
            else:
                record.available_sale_order_ids = False

    @api.depends('partner_id')
    def _compute_delivery_notes(self):
        """Compute delivery notes for the selected customer"""
        for record in self:
            if record.partner_id:
                # Find deliveries for this customer
                deliveries = self.env['stock.picking'].search([
                    ('partner_id', '=', record.partner_id.id),
                    ('picking_type_code', '=', 'outgoing'),
                    ('state', '=', 'done')
                ], limit=20)  # Limit to recent 20
                record.delivery_note_ids = deliveries
            else:
                record.delivery_note_ids = False

    @api.onchange('partner_id')
    def _onchange_partner_id_clear_so(self):
        """Clear sales order when customer changes"""
        if self.partner_id:
            self.sale_order_id = False
        return {
            'domain': {
                'sale_order_id': [
                    ('partner_id', '=', self.partner_id.id),
                    ('state', 'in', ['sale', 'done']),
                    ('invoice_status', 'in', ['to invoice', 'invoiced'])
                ]
            }
        }

    @api.onchange('sale_order_id')
    def _onchange_sale_order_id(self):
        """Populate invoice lines from selected sales order"""
        if self.sale_order_id and self.move_type in ['out_invoice', 'out_refund']:
            # Clear existing lines
            self.invoice_line_ids = [(5, 0, 0)]

            # Create invoice lines from sales order lines
            invoice_lines = []
            for line in self.sale_order_id.order_line:
                # Skip lines without products or display type lines
                if not line.product_id or line.display_type:
                    continue

                # Only add lines that need to be invoiced
                qty_to_invoice = line.product_uom_qty - line.qty_invoiced

                if qty_to_invoice > 0:
                    invoice_line_vals = {
                        'product_id': line.product_id.id,
                        'name': line.name,
                        'quantity': qty_to_invoice,
                        'price_unit': line.price_unit,
                        'tax_ids': [(6, 0, line.tax_ids.ids)],
                        'sale_line_ids': [(6, 0, [line.id])],
                    }

                    # Set account if available
                    account = line.product_id.property_account_income_id or \
                              line.product_id.categ_id.property_account_income_categ_id
                    if account:
                        invoice_line_vals['account_id'] = account.id

                    invoice_lines.append((0, 0, invoice_line_vals))

            if invoice_lines:
                self.invoice_line_ids = invoice_lines

            # CRITICAL: Link invoice to sales order using invoice_origin
            self.invoice_origin = self.sale_order_id.name
            self.payment_reference = self.sale_order_id.name

            # Set PO Number and Customer Reference from Sales Order
            if hasattr(self.sale_order_id, 'client_order_ref') and self.sale_order_id.client_order_ref:
                self.client_order_ref = self.sale_order_id.client_order_ref
                self.ref = self.sale_order_id.client_order_ref

            # Set AWB Number from Sales Order
            if hasattr(self.sale_order_id, 'awb_number') and self.sale_order_id.awb_number:
                if hasattr(self, 'awb_number'):
                    self.awb_number = self.sale_order_id.awb_number

            # Set fiscal position if available
            if self.sale_order_id.fiscal_position_id:
                self.fiscal_position_id = self.sale_order_id.fiscal_position_id

            # Get delivery information from related picking
            picking = self.env['stock.picking'].search([
                ('sale_id', '=', self.sale_order_id.id),
                ('picking_type_code', '=', 'outgoing'),
                ('state', '=', 'done')
            ], limit=1, order='date_done desc')

            if picking:
                # Set Delivery Note Number
                if hasattr(self, 'l10n_in_shipping_bill_number'):
                    self.l10n_in_shipping_bill_number = picking.name
                elif hasattr(self, 'delivery_note_number'):
                    self.delivery_note_number = picking.name

    def _post(self, soft=True):
        """Override _post to update sales order after invoice confirmation"""
        res = super(AccountMove, self)._post(soft)

        for move in self:
            if move.state == 'posted' and move.move_type == 'out_invoice' and move.sale_order_id:
                _logger.info(f"Updating sales order {move.sale_order_id.name} after invoice {move.name} confirmation")

                # Update qty_invoiced on sale order lines
                for inv_line in move.invoice_line_ids:
                    if inv_line.sale_line_ids:
                        for so_line in inv_line.sale_line_ids:
                            # Odoo should handle this automatically, but we ensure it
                            so_line._compute_qty_invoiced()

                # Force recompute invoice status
                move.sale_order_id._compute_invoice_status()

                _logger.info(
                    f"Sales order {move.sale_order_id.name} updated - invoice_status: {move.sale_order_id.invoice_status}, invoice_count: {move.sale_order_id.invoice_count}")

        return res

    def button_draft(self):
        """Override to handle sales order when resetting to draft"""
        for move in self:
            if move.state == 'posted' and move.move_type == 'out_invoice' and move.sale_order_id:
                _logger.info(f"Resetting invoice {move.name} to draft")

        res = super(AccountMove, self).button_draft()

        # Recompute after resetting to draft
        for move in self:
            if move.sale_order_id:
                move.sale_order_id._compute_invoice_status()

        return res

    def button_cancel(self):
        """Override to handle sales order when canceling"""
        for move in self:
            if move.state == 'posted' and move.move_type == 'out_invoice' and move.sale_order_id:
                _logger.info(f"Canceling invoice {move.name}")

        res = super(AccountMove, self).button_cancel()

        # Recompute after canceling
        for move in self:
            if move.sale_order_id:
                move.sale_order_id._compute_invoice_status()

        return res


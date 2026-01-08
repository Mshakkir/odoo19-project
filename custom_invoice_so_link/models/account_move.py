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
#                 # Find sales orders for this customer that NEED to be invoiced
#                 # Only show orders with invoice_status = 'to invoice' (pending)
#                 orders = self.env['sale.order'].search([
#                     ('partner_id', '=', record.partner_id.id),
#                     ('state', 'in', ['sale', 'done']),
#                     ('invoice_status', '=', 'to invoice')  # Changed: only pending invoices
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
#                     ('invoice_status', '=', 'to invoice')  # Changed: only pending invoices
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
#             # Set fiscal position if available
#             if self.sale_order_id.fiscal_position_id:
#                 self.fiscal_position_id = self.sale_order_id.fiscal_position_id

from odoo import models, fields, api
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    # Field to select sales order
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sales Order',
        help="Select a sales order to create invoice from",
        copy=False
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

    @api.depends('partner_id', 'move_type')
    def _compute_available_sale_orders(self):
        """Compute available sales orders for the selected customer"""
        for record in self:
            if record.partner_id and record.move_type in ['out_invoice', 'out_refund']:
                # Find sales orders for this customer that NEED to be invoiced
                orders = self.env['sale.order'].search([
                    ('partner_id', '=', record.partner_id.id),
                    ('state', 'in', ['sale', 'done']),
                    ('invoice_status', '=', 'to invoice')
                ])
                record.available_sale_order_ids = orders
            else:
                record.available_sale_order_ids = False

    @api.depends('partner_id')
    def _compute_delivery_notes(self):
        """Compute delivery notes for the selected customer"""
        for record in self:
            if record.partner_id:
                deliveries = self.env['stock.picking'].search([
                    ('partner_id', '=', record.partner_id.id),
                    ('picking_type_code', '=', 'outgoing'),
                    ('state', '=', 'done')
                ], limit=20)
                record.delivery_note_ids = deliveries
            else:
                record.delivery_note_ids = False

    @api.onchange('partner_id')
    def _onchange_partner_id_clear_so(self):
        """Clear sales order when customer changes"""
        self.sale_order_id = False
        if self.partner_id:
            return {
                'domain': {
                    'sale_order_id': [
                        ('partner_id', '=', self.partner_id.id),
                        ('state', 'in', ['sale', 'done']),
                        ('invoice_status', '=', 'to invoice')
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
                        'product_uom_id': line.product_uom_id.id,
                    }

                    # Set account if available
                    account = line.product_id.property_account_income_id or \
                              line.product_id.categ_id.property_account_income_categ_id
                    if account:
                        invoice_line_vals['account_id'] = account.id

                    invoice_lines.append((0, 0, invoice_line_vals))

            if invoice_lines:
                self.invoice_line_ids = invoice_lines

            # Set other invoice fields from SO
            self.invoice_origin = self.sale_order_id.name
            self.payment_reference = self.sale_order_id.name

            # Set fiscal position if available
            if self.sale_order_id.fiscal_position_id:
                self.fiscal_position_id = self.sale_order_id.fiscal_position_id

    def _post(self, soft=True):
        """Override _post to update sales order after invoice confirmation"""
        # Call parent method
        posted = super(AccountMove, self)._post(soft)

        # Update sales order invoice status
        for move in posted:
            if move.sale_order_id and move.move_type == 'out_invoice' and move.state == 'posted':
                # Get all SO lines that were invoiced
                invoiced_so_lines = self.env['sale.order.line']
                for inv_line in move.invoice_line_ids:
                    if inv_line.sale_line_ids:
                        invoiced_so_lines |= inv_line.sale_line_ids

                # Manually update qty_invoiced for each SO line
                for so_line in invoiced_so_lines:
                    # Calculate total invoiced quantity from all invoice lines
                    total_invoiced = 0.0
                    invoice_lines = self.env['account.move.line'].search([
                        ('sale_line_ids', 'in', so_line.ids),
                        ('move_id.state', '=', 'posted'),
                        ('move_id.move_type', '=', 'out_invoice'),
                        ('parent_state', '=', 'posted')
                    ])

                    for inv_line in invoice_lines:
                        total_invoiced += inv_line.quantity

                    # Update the SO line
                    so_line.write({'qty_invoiced': total_invoiced})

                # Force update invoice_status on sales order
                sale_order = move.sale_order_id

                # Check if all lines are fully invoiced
                all_invoiced = True
                for line in sale_order.order_line:
                    if not line.display_type and line.product_id:
                        if line.qty_invoiced < line.product_uom_qty:
                            all_invoiced = False
                            break

                # Update invoice status
                if all_invoiced:
                    sale_order.write({'invoice_status': 'invoiced'})
                else:
                    sale_order.write({'invoice_status': 'to invoice'})

        return posted

    def button_draft(self):
        """Override to update sales order when invoice is reset to draft"""
        sale_orders = self.mapped('sale_order_id')

        res = super(AccountMove, self).button_draft()

        # Update sales orders invoice status
        for so in sale_orders:
            # Recalculate qty_invoiced for each line
            for line in so.order_line:
                if not line.display_type and line.product_id:
                    total_invoiced = 0.0
                    invoice_lines = self.env['account.move.line'].search([
                        ('sale_line_ids', 'in', line.ids),
                        ('move_id.state', '=', 'posted'),
                        ('move_id.move_type', '=', 'out_invoice')
                    ])

                    for inv_line in invoice_lines:
                        total_invoiced += inv_line.quantity

                    line.write({'qty_invoiced': total_invoiced})

            # Update invoice status
            any_to_invoice = any(
                line.qty_invoiced < line.product_uom_qty
                for line in so.order_line
                if not line.display_type and line.product_id
            )

            if any_to_invoice:
                so.write({'invoice_status': 'to invoice'})

        return res

    def button_cancel(self):
        """Override to update sales order when invoice is cancelled"""
        return self.button_draft()
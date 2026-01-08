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
                # Find deliveries for this customer
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
        if self.partner_id:
            self.sale_order_id = False
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
                        'sale_line_ids': [(6, 0, [line.id])],  # Link to SO line
                        'product_uom_id': line.product_uom.id,
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

    def action_post(self):
        """Override to update sales order invoice status when invoice is posted"""
        res = super(AccountMove, self).action_post()

        # Update sales order invoice status
        for move in self:
            if move.sale_order_id and move.move_type == 'out_invoice':
                # Force recompute of invoice status on the sales order
                move.sale_order_id._get_invoiced()

        return res

    def button_draft(self):
        """Override to update sales order when invoice is reset to draft"""
        res = super(AccountMove, self).button_draft()

        # Update sales order invoice status
        for move in self:
            if move.sale_order_id:
                # Force recompute of invoice status on the sales order
                move.sale_order_id._get_invoiced()

        return res

    def button_cancel(self):
        """Override to update sales order when invoice is cancelled"""
        res = super(AccountMove, self).button_cancel()

        # Update sales order invoice status
        for move in self:
            if move.sale_order_id:
                # Force recompute of invoice status on the sales order
                move.sale_order_id._get_invoiced()

        return res


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _compute_sale_order_line_fields(self):
        """Ensure sale_line_ids are properly set"""
        super(AccountMoveLine, self)._compute_sale_order_line_fields()
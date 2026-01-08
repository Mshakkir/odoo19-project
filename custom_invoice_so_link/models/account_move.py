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
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sales Order',
        help="Select a sales order to create invoice from",
        copy=False
    )

    available_sale_order_ids = fields.Many2many(
        'sale.order',
        compute='_compute_available_sale_orders',
        string='Available Sales Orders'
    )

    delivery_note_ids = fields.Many2many(
        'stock.picking',
        string='Delivery Notes',
        compute='_compute_delivery_notes',
        help="Delivery notes related to this customer"
    )

    @api.depends('partner_id', 'move_type')
    def _compute_available_sale_orders(self):
        for record in self:
            if record.partner_id and record.move_type in ['out_invoice', 'out_refund']:
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
            self.invoice_line_ids = [(5, 0, 0)]

            invoice_lines = []
            for line in self.sale_order_id.order_line:
                if not line.product_id or line.display_type:
                    continue

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

                    account = line.product_id.property_account_income_id or \
                              line.product_id.categ_id.property_account_income_categ_id
                    if account:
                        invoice_line_vals['account_id'] = account.id

                    invoice_lines.append((0, 0, invoice_line_vals))

            if invoice_lines:
                self.invoice_line_ids = invoice_lines

            self.invoice_origin = self.sale_order_id.name
            self.payment_reference = self.sale_order_id.name

            if self.sale_order_id.fiscal_position_id:
                self.fiscal_position_id = self.sale_order_id.fiscal_position_id

    def write(self, vals):
        """Override write to ensure sale_order_id is saved"""
        res = super(AccountMove, self).write(vals)

        # If sale_order_id is being set, ensure invoice_origin is set
        if 'sale_order_id' in vals and vals['sale_order_id']:
            for move in self:
                if move.sale_order_id and not move.invoice_origin:
                    move.invoice_origin = move.sale_order_id.name

        return res

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to ensure sale_order_id relationship is saved"""
        moves = super(AccountMove, self).create(vals_list)

        for move in moves:
            if move.sale_order_id and not move.invoice_origin:
                move.invoice_origin = move.sale_order_id.name

        return moves

    def _post(self, soft=True):
        """Override _post to update sales order after invoice confirmation"""
        res = super(AccountMove, self)._post(soft)

        for move in self.filtered(lambda m: m.state == 'posted'):
            if move.sale_order_id and move.move_type == 'out_invoice':
                _logger.info(f"📝 Processing invoice {move.name} for SO {move.sale_order_id.name}")

                # Update qty_invoiced for each sale order line
                for inv_line in move.invoice_line_ids.filtered(lambda l: l.product_id and not l.display_type):
                    # Find the corresponding SO line(s)
                    if inv_line.sale_line_ids:
                        # Already linked via sale_line_ids
                        for so_line in inv_line.sale_line_ids:
                            new_qty = so_line.qty_invoiced + inv_line.quantity
                            so_line.write({'qty_invoiced': new_qty})
                            _logger.info(f"   Updated SO line {so_line.id}: qty_invoiced = {new_qty}")
                    else:
                        # Try to find matching SO line by product
                        matching_lines = move.sale_order_id.order_line.filtered(
                            lambda l: l.product_id == inv_line.product_id and
                                      not l.display_type and
                                      l.qty_to_invoice > 0
                        )

                        if matching_lines:
                            so_line = matching_lines[0]
                            # Link the invoice line to SO line
                            inv_line.write({'sale_line_ids': [(6, 0, [so_line.id])]})
                            # Update qty_invoiced
                            new_qty = so_line.qty_invoiced + inv_line.quantity
                            so_line.write({'qty_invoiced': new_qty})
                            _logger.info(f"   Linked and updated SO line {so_line.id}: qty_invoiced = {new_qty}")

                # Force recompute of invoice_status
                move.sale_order_id._compute_invoice_status()
                move.sale_order_id.invalidate_recordset(['invoice_status'])

                _logger.info(f"   ✅ SO {move.sale_order_id.name} invoice_status: {move.sale_order_id.invoice_status}")

        return res

    def button_draft(self):
        """Override button_draft to handle sales order when resetting to draft"""
        res = super(AccountMove, self).button_draft()

        for move in self:
            if move.sale_order_id and move.move_type == 'out_invoice':
                _logger.info(f"🔄 Resetting invoice {move.name} to draft for SO {move.sale_order_id.name}")

                # Decrease qty_invoiced for each sale order line
                for inv_line in move.invoice_line_ids.filtered(lambda l: l.sale_line_ids):
                    for so_line in inv_line.sale_line_ids:
                        new_qty = max(0, so_line.qty_invoiced - inv_line.quantity)
                        so_line.write({'qty_invoiced': new_qty})
                        _logger.info(f"   Decreased SO line {so_line.id}: qty_invoiced = {new_qty}")

                # Force recompute of invoice_status
                move.sale_order_id._compute_invoice_status()
                move.sale_order_id.invalidate_recordset(['invoice_status'])

        return res

    def button_cancel(self):
        """Override button_cancel to handle sales order when canceling"""
        for move in self:
            if move.sale_order_id and move.move_type == 'out_invoice' and move.state == 'posted':
                _logger.info(f"❌ Canceling invoice {move.name} for SO {move.sale_order_id.name}")

                # Decrease qty_invoiced for each sale order line
                for inv_line in move.invoice_line_ids.filtered(lambda l: l.sale_line_ids):
                    for so_line in inv_line.sale_line_ids:
                        new_qty = max(0, so_line.qty_invoiced - inv_line.quantity)
                        so_line.write({'qty_invoiced': new_qty})
                        _logger.info(f"   Decreased SO line {so_line.id}: qty_invoiced = {new_qty}")

                # Force recompute of invoice_status
                move.sale_order_id._compute_invoice_status()
                move.sale_order_id.invalidate_recordset(['invoice_status'])

        res = super(AccountMove, self).button_cancel()
        return res
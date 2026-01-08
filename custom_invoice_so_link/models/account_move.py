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

    def action_post(self):
        """Override action_post to update sales order"""
        res = super(AccountMove, self).action_post()

        for move in self:
            if move.sale_order_id and move.move_type == 'out_invoice':
                _logger.info(f"🔵 Updating sales order {move.sale_order_id.name} after invoice post")

                # Update each SO line manually using direct SQL
                for inv_line in move.invoice_line_ids.filtered(lambda l: l.sale_line_ids):
                    for so_line in inv_line.sale_line_ids:
                        # Calculate new qty_invoiced
                        new_qty = so_line.qty_invoiced + inv_line.quantity

                        # Direct SQL update
                        self.env.cr.execute("""
                            UPDATE sale_order_line 
                            SET qty_invoiced = %s
                            WHERE id = %s
                        """, (new_qty, so_line.id))

                        _logger.info(f"   Updated SO line {so_line.id}: qty_invoiced = {new_qty}")

                # Force database commit
                self.env.cr.commit()

                # Refresh the sales order from database
                move.sale_order_id.invalidate_recordset(['invoice_status'])
                move.sale_order_id.order_line.invalidate_recordset(['qty_invoiced'])

                # Check if all lines are fully invoiced
                all_lines = move.sale_order_id.order_line.filtered(lambda l: l.product_id and not l.display_type)

                # Refresh data from DB
                all_lines_data = self.env.cr.execute("""
                    SELECT id, product_uom_qty, qty_invoiced 
                    FROM sale_order_line 
                    WHERE id IN %s
                """, (tuple(all_lines.ids),))

                all_invoiced = True
                for line in all_lines:
                    if line.qty_invoiced < line.product_uom_qty:
                        all_invoiced = False
                        break

                # Update invoice_status
                if all_invoiced:
                    self.env.cr.execute("""
                        UPDATE sale_order 
                        SET invoice_status = 'invoiced'
                        WHERE id = %s
                    """, (move.sale_order_id.id,))
                    self.env.cr.commit()
                    _logger.info(f"   ✅ Sales order {move.sale_order_id.name} marked as INVOICED")
                else:
                    _logger.info(f"   ⚠️ Sales order {move.sale_order_id.name} partially invoiced")

        return res
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
        copy=False,
        states={'posted': [('readonly', True)], 'cancel': [('readonly', True)]}
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
            _logger.info(f"🔵 onchange triggered for SO: {self.sale_order_id.name}")

            # Clear existing lines
            self.invoice_line_ids = [(5, 0, 0)]

            invoice_lines = []
            for line in self.sale_order_id.order_line:
                if not line.product_id or line.display_type:
                    continue

                qty_to_invoice = line.product_uom_qty - line.qty_invoiced

                _logger.info(f"  Processing line: {line.product_id.name}")
                _logger.info(
                    f"    Ordered: {line.product_uom_qty}, Invoiced: {line.qty_invoiced}, To Invoice: {qty_to_invoice}")

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
                    _logger.info(f"    ✅ Added to invoice with sale_line_ids: [{line.id}]")

            if invoice_lines:
                self.invoice_line_ids = invoice_lines
                _logger.info(f"✅ Created {len(invoice_lines)} invoice lines")

            # Set invoice metadata
            self.invoice_origin = self.sale_order_id.name
            self.payment_reference = self.sale_order_id.name

            if self.sale_order_id.fiscal_position_id:
                self.fiscal_position_id = self.sale_order_id.fiscal_position_id

    def _post(self, soft=True):
        """Override _post to update sales order after invoice confirmation"""
        _logger.info("🟢 _post() called")

        # Call parent first
        res = super(AccountMove, self)._post(soft)

        # Process each posted invoice
        for move in self.filtered(lambda m: m.state == 'posted' and m.move_type == 'out_invoice'):
            _logger.info(f"📝 Processing posted invoice: {move.name}")
            _logger.info(f"   sale_order_id: {move.sale_order_id.name if move.sale_order_id else 'NOT SET'}")

            if not move.sale_order_id:
                _logger.warning(f"   ⚠️ No sale_order_id set on invoice {move.name}")
                continue

            sale_order = move.sale_order_id
            _logger.info(f"   Processing SO: {sale_order.name}")
            _logger.info(f"   SO current invoice_status: {sale_order.invoice_status}")

            # Process each invoice line
            updated_lines = []
            for inv_line in move.invoice_line_ids.filtered(lambda l: l.product_id and not l.display_type):
                _logger.info(f"   Invoice line: {inv_line.product_id.name}, qty: {inv_line.quantity}")
                _logger.info(f"     sale_line_ids: {inv_line.sale_line_ids.ids}")

                if inv_line.sale_line_ids:
                    # Line is already linked - update qty_invoiced
                    for so_line in inv_line.sale_line_ids:
                        old_qty = so_line.qty_invoiced
                        new_qty = old_qty + inv_line.quantity
                        so_line.qty_invoiced = new_qty
                        updated_lines.append(so_line.id)
                        _logger.info(f"     ✅ Updated SO line {so_line.id}: {old_qty} → {new_qty}")
                else:
                    # Line not linked - try to find matching SO line
                    _logger.warning(f"     ⚠️ Invoice line has no sale_line_ids!")
                    matching_lines = sale_order.order_line.filtered(
                        lambda l: l.product_id == inv_line.product_id and
                                  not l.display_type and
                                  l.qty_to_invoice > 0
                    )

                    if matching_lines:
                        so_line = matching_lines[0]
                        # Link it
                        inv_line.sale_line_ids = [(6, 0, [so_line.id])]
                        # Update qty
                        old_qty = so_line.qty_invoiced
                        new_qty = old_qty + inv_line.quantity
                        so_line.qty_invoiced = new_qty
                        updated_lines.append(so_line.id)
                        _logger.info(f"     🔗 Linked and updated SO line {so_line.id}: {old_qty} → {new_qty}")

            if updated_lines:
                _logger.info(f"   Updated {len(set(updated_lines))} SO lines")
                # Force recompute
                sale_order.order_line.invalidate_recordset(['qty_invoiced', 'qty_to_invoice'])
                sale_order.invalidate_recordset(['invoice_status'])
                sale_order._compute_invoice_status()
                _logger.info(f"   ✅ SO {sale_order.name} new invoice_status: {sale_order.invoice_status}")
            else:
                _logger.warning(f"   ⚠️ No SO lines were updated!")

        return res

    def button_draft(self):
        """Override button_draft to handle sales order when resetting to draft"""
        _logger.info("🔄 button_draft() called")

        for move in self:
            if move.sale_order_id and move.move_type == 'out_invoice' and move.state == 'posted':
                _logger.info(f"   Resetting invoice {move.name} for SO {move.sale_order_id.name}")

                # Decrease qty_invoiced
                for inv_line in move.invoice_line_ids.filtered(lambda l: l.sale_line_ids):
                    for so_line in inv_line.sale_line_ids:
                        old_qty = so_line.qty_invoiced
                        new_qty = max(0, old_qty - inv_line.quantity)
                        so_line.qty_invoiced = new_qty
                        _logger.info(f"     Decreased SO line {so_line.id}: {old_qty} → {new_qty}")

                # Recompute
                move.sale_order_id.order_line.invalidate_recordset(['qty_invoiced', 'qty_to_invoice'])
                move.sale_order_id.invalidate_recordset(['invoice_status'])
                move.sale_order_id._compute_invoice_status()

        res = super(AccountMove, self).button_draft()
        return res

    def button_cancel(self):
        """Override button_cancel to handle sales order when canceling"""
        _logger.info("❌ button_cancel() called")

        for move in self:
            if move.sale_order_id and move.move_type == 'out_invoice' and move.state == 'posted':
                _logger.info(f"   Canceling invoice {move.name} for SO {move.sale_order_id.name}")

                # Decrease qty_invoiced
                for inv_line in move.invoice_line_ids.filtered(lambda l: l.sale_line_ids):
                    for so_line in inv_line.sale_line_ids:
                        old_qty = so_line.qty_invoiced
                        new_qty = max(0, old_qty - inv_line.quantity)
                        so_line.qty_invoiced = new_qty
                        _logger.info(f"     Decreased SO line {so_line.id}: {old_qty} → {new_qty}")

                # Recompute
                move.sale_order_id.order_line.invalidate_recordset(['qty_invoiced', 'qty_to_invoice'])
                move.sale_order_id.invalidate_recordset(['invoice_status'])
                move.sale_order_id._compute_invoice_status()

        res = super(AccountMove, self).button_cancel()
        return res

    def action_check_so_link(self):
        """Debug action to check SO linkage"""
        for move in self:
            _logger.info("=" * 80)
            _logger.info(f"DIAGNOSTIC FOR INVOICE: {move.name}")
            _logger.info("=" * 80)

            _logger.info(f"Invoice ID: {move.id}")
            _logger.info(f"State: {move.state}")
            _logger.info(f"Move Type: {move.move_type}")
            _logger.info(f"Partner: {move.partner_id.name}")
            _logger.info(f"Sale Order ID field: {move.sale_order_id.name if move.sale_order_id else 'NOT SET'}")
            _logger.info(f"Invoice Origin: {move.invoice_origin}")

            _logger.info("\n--- INVOICE LINES ---")
            for line in move.invoice_line_ids:
                if line.display_type:
                    continue
                _logger.info(f"  Line {line.id}: {line.product_id.name if line.product_id else 'No Product'}")
                _logger.info(f"    Quantity: {line.quantity}")
                _logger.info(f"    sale_line_ids: {line.sale_line_ids.ids}")

            if move.sale_order_id:
                _logger.info(f"\n--- SALES ORDER: {move.sale_order_id.name} ---")
                _logger.info(f"  SO State: {move.sale_order_id.state}")
                _logger.info(f"  Invoice Status: {move.sale_order_id.invoice_status}")

                _logger.info("\n--- SO LINES ---")
                for so_line in move.sale_order_id.order_line:
                    if so_line.display_type:
                        continue
                    _logger.info(f"  SO Line {so_line.id}: {so_line.product_id.name}")
                    _logger.info(f"    Ordered Qty: {so_line.product_uom_qty}")
                    _logger.info(f"    Invoiced Qty: {so_line.qty_invoiced}")
                    _logger.info(f"    To Invoice: {so_line.qty_to_invoice}")

            _logger.info("=" * 80)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Diagnostic Complete',
                'message': 'Check server logs for details',
                'type': 'success',
            }
        }
# from odoo import models, fields, api
#
#
# class AccountMove(models.Model):
#     _inherit = 'account.move'
#
#     # Field to select multiple sales orders
#     sale_order_ids = fields.Many2many(
#         'sale.order',
#         'account_move_sale_order_rel',
#         'move_id',
#         'order_id',
#         string='Sales Orders',
#         help="Select multiple sales orders to create invoice from"
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
#                 orders = self.env['sale.order'].search([
#                     ('partner_id', '=', record.partner_id.id),
#                     ('state', 'in', ['sale', 'done']),
#                     ('invoice_status', 'in', ['to invoice'])
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
#                 deliveries = self.env['stock.picking'].search([
#                     ('partner_id', '=', record.partner_id.id),
#                     ('picking_type_code', '=', 'outgoing'),
#                     ('state', '=', 'done')
#                 ], limit=20)
#                 record.delivery_note_ids = deliveries
#             else:
#                 record.delivery_note_ids = False
#
#     @api.onchange('partner_id')
#     def _onchange_partner_id_clear_so(self):
#         """Clear sales orders when customer changes"""
#         if self.partner_id:
#             self.sale_order_ids = [(5, 0, 0)]
#         return {
#             'domain': {
#                 'sale_order_ids': [
#                     ('partner_id', '=', self.partner_id.id),
#                     ('state', 'in', ['sale', 'done']),
#                     ('invoice_status', 'in', ['to invoice'])
#                 ]
#             }
#         }
#
#     @api.onchange('sale_order_ids')
#     def _onchange_sale_order_ids(self):
#         """Populate invoice lines from selected sales orders"""
#         if self.sale_order_ids and self.move_type in ['out_invoice', 'out_refund']:
#             # Clear existing lines
#             self.invoice_line_ids = [(5, 0, 0)]
#
#             invoice_lines = []
#             origins = []
#             payment_refs = []
#             customer_refs = []
#             awb_numbers = []
#             delivery_notes = []
#
#             for order in self.sale_order_ids:
#                 origins.append(order.name)
#                 payment_refs.append(order.name)
#
#                 # Collect Customer Reference
#                 if hasattr(order, 'client_order_ref') and order.client_order_ref:
#                     customer_refs.append(order.client_order_ref)
#
#                 # Collect AWB Number
#                 if hasattr(order, 'awb_number') and order.awb_number:
#                     awb_numbers.append(order.awb_number)
#
#                 # Create invoice lines from sales order lines
#                 for line in order.order_line:
#                     if not line.product_id or line.display_type:
#                         continue
#
#                     qty_to_invoice = line.product_uom_qty - line.qty_invoiced
#
#                     if qty_to_invoice > 0:
#                         invoice_line_vals = {
#                             'product_id': line.product_id.id,
#                             'name': line.name,
#                             'quantity': qty_to_invoice,
#                             'price_unit': line.price_unit,
#                             'tax_ids': [(6, 0, line.tax_ids.ids)],
#                             'sale_line_ids': [(6, 0, [line.id])],
#                         }
#
#                         account = line.product_id.property_account_income_id or \
#                                   line.product_id.categ_id.property_account_income_categ_id
#                         if account:
#                             invoice_line_vals['account_id'] = account.id
#
#                         invoice_lines.append((0, 0, invoice_line_vals))
#
#                 # Get delivery information from related picking
#                 picking = self.env['stock.picking'].search([
#                     ('sale_id', '=', order.id),
#                     ('picking_type_code', '=', 'outgoing'),
#                     ('state', '=', 'done')
#                 ], limit=1, order='date_done desc')
#
#                 if picking:
#                     delivery_notes.append(picking.name)
#
#             if invoice_lines:
#                 self.invoice_line_ids = invoice_lines
#
#             # Set combined values
#             self.invoice_origin = ', '.join(origins)
#             self.payment_reference = ', '.join(payment_refs)
#
#             # Set Customer Reference
#             if customer_refs:
#                 self.ref = ', '.join(customer_refs)
#
#             # Set AWB Number
#             if awb_numbers and hasattr(self, 'awb_number'):
#                 self.awb_number = ', '.join(awb_numbers)
#
#             # Set Delivery Note Number
#             if delivery_notes:
#                 if hasattr(self, 'l10n_in_shipping_bill_number'):
#                     self.l10n_in_shipping_bill_number = ', '.join(delivery_notes)
#                 elif hasattr(self, 'delivery_note_number'):
#                     self.delivery_note_number = ', '.join(delivery_notes)
#
#             # Set fiscal position from first order
#             if self.sale_order_ids and self.sale_order_ids[0].fiscal_position_id:
#                 self.fiscal_position_id = self.sale_order_ids[0].fiscal_position_id

from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    # Field to select multiple sales orders
    sale_order_ids = fields.Many2many(
        'sale.order',
        'account_move_sale_order_rel',
        'move_id',
        'order_id',
        string='Sales Orders',
        help="Select multiple sales orders to create invoice from"
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
                orders = self.env['sale.order'].search([
                    ('partner_id', '=', record.partner_id.id),
                    ('state', 'in', ['sale', 'done']),
                    ('invoice_status', 'in', ['to invoice'])
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
        """Clear sales orders when customer changes"""
        if self.partner_id:
            self.sale_order_ids = [(5, 0, 0)]
        return {
            'domain': {
                'sale_order_ids': [
                    ('partner_id', '=', self.partner_id.id),
                    ('state', 'in', ['sale', 'done']),
                    ('invoice_status', 'in', ['to invoice'])
                ]
            }
        }

    @api.onchange('sale_order_ids')
    def _onchange_sale_order_ids(self):
        """Populate invoice lines from selected sales orders"""
        if self.sale_order_ids and self.move_type in ['out_invoice', 'out_refund']:
            # Clear existing lines
            self.invoice_line_ids = [(5, 0, 0)]

            invoice_lines = []
            origins = []
            payment_refs = []
            customer_refs = []
            awb_numbers = []
            delivery_notes = []

            for order in self.sale_order_ids:
                origins.append(order.name)
                payment_refs.append(order.name)

                # Collect Customer Reference
                if hasattr(order, 'client_order_ref') and order.client_order_ref:
                    customer_refs.append(order.client_order_ref)

                # Collect AWB Number
                if hasattr(order, 'awb_number') and order.awb_number:
                    awb_numbers.append(order.awb_number)

                # Create invoice lines from sales order lines
                for line in order.order_line:
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
                        }

                        account = line.product_id.property_account_income_id or \
                                  line.product_id.categ_id.property_account_income_categ_id
                        if account:
                            invoice_line_vals['account_id'] = account.id

                        invoice_lines.append((0, 0, invoice_line_vals))

                # Get delivery information from related picking
                picking = self.env['stock.picking'].search([
                    ('sale_id', '=', order.id),
                    ('picking_type_code', '=', 'outgoing'),
                    ('state', '=', 'done')
                ], limit=1, order='date_done desc')

                if picking:
                    delivery_notes.append(picking.name)

            if invoice_lines:
                self.invoice_line_ids = invoice_lines

            # Set combined values
            self.invoice_origin = ', '.join(origins)
            self.payment_reference = ', '.join(payment_refs)

            # Set Customer Reference
            if customer_refs:
                self.ref = ', '.join(customer_refs)

            # Set AWB Number
            if awb_numbers and hasattr(self, 'awb_number'):
                self.awb_number = ', '.join(awb_numbers)

            # Set Delivery Note Number
            if delivery_notes:
                if hasattr(self, 'l10n_in_shipping_bill_number'):
                    self.l10n_in_shipping_bill_number = ', '.join(delivery_notes)
                elif hasattr(self, 'delivery_note_number'):
                    self.delivery_note_number = ', '.join(delivery_notes)

            # Set fiscal position from first order
            if self.sale_order_ids and self.sale_order_ids[0].fiscal_position_id:
                self.fiscal_position_id = self.sale_order_ids[0].fiscal_position_id

    @api.model
    def create(self, vals):
        """Override create to ensure sales orders are linked when invoice is created"""
        record = super().create(vals)

        # The Many2many relationship is automatically created
        # Odoo automatically populates invoice_ids on the sale orders
        # So the sales order status will automatically update to "fully invoiced"

        return record

    def action_post(self):
        """Override action_post to ensure proper linking when invoice is posted"""
        result = super().action_post()

        # Refresh sale orders to update their invoice status
        # This ensures the sales order status changes to "fully invoiced"
        if self.sale_order_ids:
            self.sale_order_ids.onchange_order_line()

        return result
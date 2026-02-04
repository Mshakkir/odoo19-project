
# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrderInvoiceWizard(models.TransientModel):
    _name = 'sale.order.invoice.wizard'
    _description = 'Create Invoice from Sale Orders'

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        domain=[('customer_rank', '>', 0)],
        help='Select the customer to view their uninvoiced sale orders'
    )

    sale_order_ids = fields.Many2many(
        'sale.order',
        string='Sale Orders',
        domain="[('partner_id', '=', partner_id), ('invoice_status', '=', 'to invoice'), ('state', '=', 'sale')]",
        help='Select the sale orders to invoice'
    )

    mode = fields.Selection([
        ('new_invoice', 'Create New Invoice'),
        ('add_to_invoice', 'Add to Current Invoice')
    ], string='Mode', default='new_invoice')

    invoice_id = fields.Many2one('account.move', string='Current Invoice')

    @api.model
    def default_get(self, fields_list):
        """Get default values from context"""
        res = super().default_get(fields_list)

        # Check if called from invoice form
        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')

        if active_model == 'account.move' and active_id:
            invoice = self.env['account.move'].browse(active_id)
            if invoice.move_type == 'out_invoice' and invoice.state == 'draft':
                res['mode'] = 'add_to_invoice'
                res['invoice_id'] = invoice.id
                if invoice.partner_id:
                    res['partner_id'] = invoice.partner_id.id

        return res

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """Clear selected sale orders when customer changes"""
        self.sale_order_ids = [(5, 0, 0)]

        # Return domain for sale_order_ids
        if self.partner_id:
            return {
                'domain': {
                    'sale_order_ids': [
                        ('partner_id', '=', self.partner_id.id),
                        ('invoice_status', '=', 'to invoice'),
                        ('state', '=', 'sale')
                    ]
                }
            }
        else:
            return {
                'domain': {
                    'sale_order_ids': [('id', '=', False)]
                }
            }

    def action_create_invoices(self):
        """Create invoice(s) from selected sale orders or add to existing invoice"""
        self.ensure_one()

        if not self.sale_order_ids:
            raise UserError(_('Please select at least one sale order to invoice.'))

        # Mode: Add to existing invoice
        if self.mode == 'add_to_invoice' and self.invoice_id:
            return self._add_to_existing_invoice()

        # Mode: Create new invoice(s)
        return self._create_new_invoices()

    def _add_to_existing_invoice(self):
        """Add sale order lines to existing draft invoice"""
        self.ensure_one()

        if self.invoice_id.state != 'draft':
            raise UserError(_('Can only add lines to draft invoices.'))

        if self.invoice_id.partner_id != self.partner_id:
            raise UserError(_('Invoice customer must match sale order customer.'))

        # Get invoiceable lines from selected sale orders
        invoice_lines = []
        for order in self.sale_order_ids:
            # Create invoice lines from sale order lines
            invoiceable_lines = order.order_line.filtered(
                lambda l: not l.display_type and l.qty_to_invoice > 0
            )

            for line in invoiceable_lines:
                # Prepare invoice line values
                line_vals = line._prepare_invoice_line()
                invoice_lines.append((0, 0, line_vals))

        # Add all lines to the invoice at once
        if invoice_lines:
            self.invoice_id.write({
                'invoice_line_ids': invoice_lines
            })

        # Return to the invoice
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
            'view_id': self.env.ref('account.view_move_form').id,
        }

    def _create_new_invoices(self):
        """Create new invoice(s) from selected sale orders"""
        self.ensure_one()

        # Use the same method as Odoo's default batch invoicing
        invoices = self.sale_order_ids._create_invoices()

        if not invoices:
            raise UserError(_('No invoice was created. Please check the sale orders.'))

        # Return action to view created invoice(s)
        action = self.env['ir.actions.act_window']._for_xml_id('account.action_move_out_invoice_type')

        if len(invoices) == 1:
            # Single invoice - open form view
            action['views'] = [(False, 'form')]
            action['res_id'] = invoices.id
        else:
            # Multiple invoices - open list view
            action['domain'] = [('id', 'in', invoices.ids)]

        return action
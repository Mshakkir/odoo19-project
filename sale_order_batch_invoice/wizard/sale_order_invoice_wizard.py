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
        """Create invoice(s) from selected sale orders"""
        self.ensure_one()

        if not self.sale_order_ids:
            raise UserError(_('Please select at least one sale order to invoice.'))

        # Use the same method as Odoo's default batch invoicing
        # This ensures consistency with the standard behavior
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
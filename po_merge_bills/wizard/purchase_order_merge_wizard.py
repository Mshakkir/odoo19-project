# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PurchaseOrderMergeWizard(models.TransientModel):
    _name = 'purchase.order.merge.wizard'
    _description = 'Merge Purchase Orders into One Bill'

    purchase_order_ids = fields.Many2many(
        'purchase.order',
        string='Purchase Orders',
        required=True
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Vendor',
        readonly=True
    )
    order_count = fields.Integer(
        string='Number of Orders',
        readonly=True
    )
    total_amount = fields.Monetary(
        string='Total Amount',
        readonly=True,
        currency_field='currency_id'
    )
    currency_id = fields.Many2one(
        'res.currency',
        readonly=True
    )
    warning_message = fields.Text(
        string='Warning',
        readonly=True
    )

    @api.model
    def default_get(self, fields_list):
        """Populate wizard with selected purchase orders"""
        res = super(PurchaseOrderMergeWizard, self).default_get(fields_list)

        # Get selected purchase orders from context
        active_ids = self.env.context.get('active_ids', [])
        purchase_orders = self.env['purchase.order'].browse(active_ids)

        if not purchase_orders:
            raise UserError(_('No purchase orders selected.'))

        # Validate all orders are from the same vendor
        vendors = purchase_orders.mapped('partner_id')
        if len(vendors) > 1:
            raise UserError(_(
                'All selected purchase orders must be from the same vendor.\n'
                'Selected vendors: %s'
            ) % ', '.join(vendors.mapped('name')))

        # Validate all orders are in valid state
        invalid_orders = purchase_orders.filtered(
            lambda po: po.state not in ['purchase', 'done']
        )
        if invalid_orders:
            raise UserError(_(
                'Only confirmed purchase orders can be merged.\n'
                'Invalid orders: %s'
            ) % ', '.join(invalid_orders.mapped('name')))

        # Check if orders already have bills
        orders_with_bills = purchase_orders.filtered(
            lambda po: po.invoice_ids
        )
        warning_message = ''
        if orders_with_bills:
            warning_message = _(
                'Warning: The following orders already have bills created:\n%s\n\n'
                'Proceeding will create additional bills for these orders.'
            ) % '\n'.join(orders_with_bills.mapped('name'))

        # Calculate totals
        total_amount = sum(purchase_orders.mapped('amount_total'))

        res.update({
            'purchase_order_ids': [(6, 0, active_ids)],
            'partner_id': vendors[0].id if vendors else False,
            'order_count': len(purchase_orders),
            'total_amount': total_amount,
            'currency_id': purchase_orders[0].currency_id.id if purchase_orders else False,
            'warning_message': warning_message,
        })

        return res

    def action_merge_bills(self):
        """Create a single bill from multiple purchase orders"""
        self.ensure_one()

        if not self.purchase_order_ids:
            raise UserError(_('No purchase orders to merge.'))

        # Get the first purchase order to use as template
        first_order = self.purchase_order_ids[0]

        # Prepare bill values
        bill_vals = {
            'move_type': 'in_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': fields.Date.context_today(self),
            'currency_id': self.currency_id.id,
            'invoice_origin': ', '.join(self.purchase_order_ids.mapped('name')),
            'ref': ', '.join(filter(None, self.purchase_order_ids.mapped('partner_ref'))),
            'invoice_line_ids': [],
        }

        # Collect all invoice lines from all purchase orders
        invoice_lines = []
        for purchase_order in self.purchase_order_ids:
            for line in purchase_order.order_line:
                # Skip lines with zero quantity
                if line.product_qty <= 0:
                    continue

                # Prepare invoice line values
                line_vals = {
                    'product_id': line.product_id.id,
                    'name': '[%s] %s' % (purchase_order.name, line.name),
                    'quantity': line.product_qty - line.qty_invoiced,
                    'product_uom_id': line.product_uom.id,
                    'price_unit': line.price_unit,
                    'tax_ids': [(6, 0, line.taxes_id.ids)],
                    'purchase_line_id': line.id,
                    'discount': line.discount if hasattr(line, 'discount') else 0.0,
                }

                # Add analytic account if exists
                if line.account_analytic_id:
                    line_vals['analytic_distribution'] = {
                        str(line.account_analytic_id.id): 100
                    }

                invoice_lines.append((0, 0, line_vals))

        if not invoice_lines:
            raise UserError(_('No lines to invoice. All lines may have been already invoiced.'))

        bill_vals['invoice_line_ids'] = invoice_lines

        # Create the bill
        bill = self.env['account.move'].create(bill_vals)

        # Link purchase orders to the bill
        for purchase_order in self.purchase_order_ids:
            purchase_order.invoice_ids = [(4, bill.id)]

        # Return action to open the created bill
        return {
            'name': _('Vendor Bill'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': bill.id,
            'target': 'current',
        }
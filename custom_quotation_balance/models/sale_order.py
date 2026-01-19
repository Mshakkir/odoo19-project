from odoo import models, fields, api
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    customer_total_invoiced = fields.Monetary(
        string='Total Invoiced',
        compute='_compute_customer_balance',
        currency_field='currency_id',
        help='Click to view all customer invoices'
    )

    customer_total_paid = fields.Monetary(
        string='Amount Paid',
        compute='_compute_customer_balance',
        currency_field='currency_id',
        help='Click to view all customer payments'
    )

    customer_balance_due = fields.Monetary(
        string='Balance Due',
        compute='_compute_customer_balance',
        currency_field='currency_id',
        help='Remaining balance (Total Invoiced - Amount Paid)'
    )

    @api.depends('partner_id')
    def _compute_customer_balance(self):
        """Calculate customer financial summary"""
        for order in self:
            if order.partner_id:
                try:
                    if 'account.move' not in self.env:
                        order.customer_total_invoiced = 0.0
                        order.customer_total_paid = 0.0
                        order.customer_balance_due = 0.0
                        continue

                    invoices = self.env['account.move'].search([
                        ('partner_id', 'child_of', order.partner_id.commercial_partner_id.id),
                        ('move_type', 'in', ['out_invoice', 'out_refund']),
                        ('state', '=', 'posted')
                    ])

                    total_invoiced = sum(invoices.filtered(
                        lambda inv: inv.move_type == 'out_invoice'
                    ).mapped('amount_total'))

                    total_refunded = sum(invoices.filtered(
                        lambda inv: inv.move_type == 'out_refund'
                    ).mapped('amount_total'))

                    total_residual = sum(invoices.mapped('amount_residual'))

                    order.customer_total_invoiced = total_invoiced - total_refunded
                    order.customer_balance_due = total_residual
                    order.customer_total_paid = order.customer_total_invoiced - order.customer_balance_due
                except Exception as e:
                    order.customer_total_invoiced = 0.0
                    order.customer_total_paid = 0.0
                    order.customer_balance_due = 0.0
            else:
                order.customer_total_invoiced = 0.0
                order.customer_total_paid = 0.0
                order.customer_balance_due = 0.0

    def action_view_customer_invoices(self):
        """Open filtered list of customer invoices - Compatible with Odoo Mates"""
        self.ensure_one()

        if not self.partner_id:
            raise UserError("Please select a customer first.")

        domain = [
            ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('state', '=', 'posted')
        ]

        invoices = self.env['account.move'].search(domain)

        if not invoices:
            raise UserError(f"No posted invoices found for {self.partner_id.name}")

        # Try to find the invoice tree view - works with both standard and Odoo Mates
        try:
            tree_view = self.env.ref('account.view_invoice_tree', raise_if_not_found=False)
            form_view = self.env.ref('account.view_move_form', raise_if_not_found=False)
        except:
            tree_view = None
            form_view = None

        views = []
        if tree_view:
            views.append((tree_view.id, 'tree'))
        if form_view:
            views.append((form_view.id, 'form'))

        # If no views found, let Odoo find them automatically
        if not views:
            views = [(False, 'tree'), (False, 'form')]

        return {
            'name': f'Invoices - {self.partner_id.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'views': views,
            'domain': domain,
            'context': {
                'create': False,
                'default_move_type': 'out_invoice',
            },
            'target': 'current',
        }

    def action_view_customer_payments(self):
        """Open filtered list of customer payments - Compatible with Odoo Mates"""
        self.ensure_one()

        if not self.partner_id:
            raise UserError("Please select a customer first.")

        domain = [
            ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
            ('partner_type', '=', 'customer'),
            ('state', '=', 'posted')
        ]

        payments = self.env['account.payment'].search(domain)

        if not payments:
            raise UserError(f"No posted payments found for {self.partner_id.name}")

        # Try to find the payment views - works with both standard and Odoo Mates
        try:
            tree_view = self.env.ref('account.view_account_payment_tree', raise_if_not_found=False)
            form_view = self.env.ref('account.view_account_payment_form', raise_if_not_found=False)
        except:
            tree_view = None
            form_view = None

        views = []
        if tree_view:
            views.append((tree_view.id, 'tree'))
        if form_view:
            views.append((form_view.id, 'form'))

        # If no views found, let Odoo find them automatically
        if not views:
            views = [(False, 'tree'), (False, 'form')]

        return {
            'name': f'Payments - {self.partner_id.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'views': views,
            'domain': domain,
            'context': {
                'create': False,
                'default_partner_id': self.partner_id.id,
                'default_partner_type': 'customer',
            },
            'target': 'current',
        }
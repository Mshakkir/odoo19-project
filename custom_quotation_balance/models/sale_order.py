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
                # Check if account.move model exists
                if 'account.move' in self.env:
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
                else:
                    # Fallback to partner's receivable balance
                    partner = order.partner_id.commercial_partner_id
                    order.customer_total_invoiced = getattr(partner, 'total_invoiced', 0.0)
                    order.customer_balance_due = getattr(partner, 'credit', 0.0)
                    order.customer_total_paid = order.customer_total_invoiced - order.customer_balance_due
            else:
                order.customer_total_invoiced = 0.0
                order.customer_total_paid = 0.0
                order.customer_balance_due = 0.0

    def action_view_customer_invoices(self):
        """Open filtered list of customer invoices"""
        self.ensure_one()

        # Check if account.move exists
        if 'account.move' not in self.env:
            raise UserError("Invoice module is not installed. Please check your accounting module.")

        invoices = self.env['account.move'].search([
            ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('state', '=', 'posted')
        ])

        # Check if there's a proper view for invoices
        try:
            # Try to get the tree view
            tree_view = self.env.ref('account.view_invoice_tree', raise_if_not_found=False)
            form_view = self.env.ref('account.view_move_form', raise_if_not_found=False)

            views = []
            if tree_view:
                views.append((tree_view.id, 'tree'))
            if form_view:
                views.append((form_view.id, 'form'))

            if not views:
                # No standard views found, let Odoo use default
                views = False

            return {
                'name': f'Invoices - {self.partner_id.name}',
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_mode': 'tree,form',
                'views': views,
                'domain': [('id', 'in', invoices.ids)],
                'context': {
                    'default_move_type': 'out_invoice',
                    'create': False,
                },
                'target': 'new',
            }
        except Exception as e:
            raise UserError(f"Error opening invoices: {str(e)}")

    def action_view_customer_payments(self):
        """Open filtered list of customer payments"""
        self.ensure_one()

        # Check if account.payment exists
        if 'account.payment' not in self.env:
            raise UserError("Payment module is not installed. Please check your accounting module.")

        payments = self.env['account.payment'].search([
            ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
            ('partner_type', '=', 'customer'),
            ('state', '=', 'posted')
        ])

        try:
            # Try to get the tree view
            tree_view = self.env.ref('account.view_account_payment_tree', raise_if_not_found=False)
            form_view = self.env.ref('account.view_account_payment_form', raise_if_not_found=False)

            views = []
            if tree_view:
                views.append((tree_view.id, 'tree'))
            if form_view:
                views.append((form_view.id, 'form'))

            if not views:
                views = False

            return {
                'name': f'Payments - {self.partner_id.name}',
                'type': 'ir.actions.act_window',
                'res_model': 'account.payment',
                'view_mode': 'tree,form',
                'views': views,
                'domain': [('id', 'in', payments.ids)],
                'context': {
                    'default_partner_id': self.partner_id.id,
                    'default_partner_type': 'customer',
                    'create': False,
                },
                'target': 'new',
            }
        except Exception as e:
            raise UserError(f"Error opening payments: {str(e)}")
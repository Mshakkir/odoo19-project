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

    def _check_accounting_module(self):
        """Check if accounting module is installed"""
        account_module = self.env['ir.module.module'].search([
            ('name', '=', 'account'),
            ('state', '=', 'installed')
        ], limit=1)

        if not account_module:
            raise UserError(
                "The Accounting/Invoicing module is not installed.\n\n"
                "Please install it first:\n"
                "1. Go to Apps menu\n"
                "2. Remove 'Apps' filter\n"
                "3. Search for 'Invoicing' or 'Accounting'\n"
                "4. Click Install"
            )
        return True

    @api.depends('partner_id')
    def _compute_customer_balance(self):
        """Calculate customer financial summary"""
        for order in self:
            if order.partner_id:
                try:
                    # Check if account.move model exists
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
        """Open filtered list of customer invoices"""
        self.ensure_one()
        self._check_accounting_module()

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

        return {
            'name': f'Invoices - {self.partner_id.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'domain': domain,
            'context': {
                'create': False,
                'default_move_type': 'out_invoice',
            },
            'view_id': False,
            'view_mode': 'tree,form',
            'target': 'current',
        }

    def action_view_customer_payments(self):
        """Open filtered list of customer payments"""
        self.ensure_one()
        self._check_accounting_module()

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

        return {
            'name': f'Payments - {self.partner_id.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'domain': domain,
            'context': {
                'create': False,
                'default_partner_id': self.partner_id.id,
                'default_partner_type': 'customer',
            },
            'view_id': False,
            'view_mode': 'tree,form',
            'target': 'current',
        }
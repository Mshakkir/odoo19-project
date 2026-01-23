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

                    # Get all customer payments (including direct payments)
                    payments = self.env['account.payment'].search([
                        ('partner_id', 'child_of', order.partner_id.commercial_partner_id.id),
                        ('partner_type', '=', 'customer'),
                        ('payment_type', '=', 'inbound'),
                        ('state', '=', 'posted')
                    ])

                    total_payments = sum(payments.mapped('amount'))
                    order.customer_total_paid = total_payments

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

        if not self.partner_id:
            raise UserError("Please select a customer first.")

        domain = [
            ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('state', '=', 'posted')
        ]

        return {
            'name': f'Invoices - {self.partner_id.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],
            'domain': domain,
            'context': {
                'create': False,
                'default_move_type': 'out_invoice',
            },
        }

    def action_view_customer_payments(self):
        """Open filtered list of customer payments"""
        self.ensure_one()

        if not self.partner_id:
            raise UserError("Please select a customer first.")

        if 'account.payment' not in self.env:
            raise UserError("Payment module is not installed.")

        domain = [
            ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
            ('partner_type', '=', 'customer'),
            ('payment_type', '=', 'inbound'),
            ('state', '=', 'posted')
        ]

        return {
            'name': f'Payments - {self.partner_id.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],
            'domain': domain,
            'context': {
                'create': False,
                'default_partner_id': self.partner_id.id,
                'default_partner_type': 'customer',
                'default_payment_type': 'inbound',
            },
        }
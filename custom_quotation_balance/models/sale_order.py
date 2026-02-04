
from odoo import models, fields, api
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Customer Balance - Using Accounting Terminology
    customer_total_invoiced = fields.Monetary(
        string='Total Debits',
        compute='_compute_customer_balance',
        currency_field='currency_id',
        help='Total debits (invoices) for this customer'
    )

    customer_total_credits = fields.Monetary(
        string='Total Credits',
        compute='_compute_customer_balance',
        currency_field='currency_id',
        help='Total credits (payments + credit notes) received from customer'
    )

    customer_balance_due = fields.Monetary(
        string='Due Amount',
        compute='_compute_customer_balance',
        currency_field='currency_id',
        help='Outstanding balance (Debits - Credits)'
    )

    @api.depends('partner_id')
    def _compute_customer_balance(self):
        """Calculate customer financial summary using accounting terminology"""
        for order in self:
            if order.partner_id:
                try:
                    if 'account.move' not in self.env:
                        order.customer_total_invoiced = 0.0
                        order.customer_total_credits = 0.0
                        order.customer_balance_due = 0.0
                        continue

                    # Get all customer invoices and credit notes
                    invoices = self.env['account.move'].search([
                        ('partner_id', 'child_of', order.partner_id.commercial_partner_id.id),
                        ('move_type', 'in', ['out_invoice', 'out_refund']),
                        ('state', '=', 'posted')
                    ])

                    # Separate invoices and credit notes
                    out_invoices = invoices.filtered(lambda inv: inv.move_type == 'out_invoice')
                    out_refunds = invoices.filtered(lambda inv: inv.move_type == 'out_refund')

                    # Total Debits = All invoices
                    total_debits = sum(out_invoices.mapped('amount_total'))
                    order.customer_total_invoiced = total_debits

                    # Get all customer payments
                    payments = self.env['account.payment'].search([
                        ('partner_id', 'child_of', order.partner_id.commercial_partner_id.id),
                        ('partner_type', '=', 'customer'),
                        ('payment_type', '=', 'inbound'),
                        ('state', 'in', ['posted', 'paid'])
                    ])

                    total_payments = sum(payments.mapped('amount'))
                    total_credit_notes = sum(out_refunds.mapped('amount_total'))

                    # Total Credits = Payments + Credit Notes
                    order.customer_total_credits = total_payments + total_credit_notes

                    # Due Amount = Debits - Credits
                    order.customer_balance_due = total_debits - (total_payments + total_credit_notes)

                except Exception as e:
                    order.customer_total_invoiced = 0.0
                    order.customer_total_credits = 0.0
                    order.customer_balance_due = 0.0
            else:
                order.customer_total_invoiced = 0.0
                order.customer_total_credits = 0.0
                order.customer_balance_due = 0.0

    def action_view_customer_invoices(self):
        """Open filtered list of customer invoices"""
        self.ensure_one()

        if not self.partner_id:
            raise UserError("Please select a customer first.")

        return {
            'name': f'Invoices - {self.partner_id.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],
            'domain': [
                ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
                ('move_type', 'in', ['out_invoice', 'out_refund']),
                ('state', '=', 'posted')
            ],
            'context': {'create': False},
        }

    def action_view_customer_credits(self):
        """Open BOTH credit notes AND advance payments - credit entries only"""
        self.ensure_one()

        if not self.partner_id:
            raise UserError("Please select a customer first.")

        return {
            'name': f'Amount Received (Credit Notes & Advance Payments) - {self.partner_id.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],
            'domain': [
                ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
                ('move_id.state', '=', 'posted'),
                ('move_id.move_type', 'in', ['out_refund', 'entry']),
                ('credit', '>', 0)
            ],
            'context': {'create': False},
        }

    def action_view_customer_payments(self):
        """Open filtered list of customer payments"""
        self.ensure_one()

        if not self.partner_id:
            raise UserError("Please select a customer first.")

        if 'account.payment' not in self.env:
            raise UserError("Payment module is not installed.")

        return {
            'name': f'Payments - {self.partner_id.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],
            'domain': [
                ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
                ('partner_type', '=', 'customer'),
                ('payment_type', '=', 'inbound'),
                ('state', 'in', ['posted', 'paid'])
            ],
            'context': {
                'create': False,
                'default_partner_id': self.partner_id.id,
                'default_partner_type': 'customer',
                'default_payment_type': 'inbound',
            },
        }
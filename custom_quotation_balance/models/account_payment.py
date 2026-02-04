

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    # Partner Balance - Using Accounting Terminology
    partner_total_invoiced = fields.Monetary(
        string='Total Debits',
        compute='_compute_partner_balance',
        currency_field='currency_id',
        help='Total debits (invoices/bills) for this partner'
    )

    partner_total_credits = fields.Monetary(
        string='Total Credits',
        compute='_compute_partner_balance',
        currency_field='currency_id',
        help='Total credits (payments + credit notes)'
    )

    partner_balance_due = fields.Monetary(
        string='Due Amount',
        compute='_compute_partner_balance',
        currency_field='currency_id',
        help='Outstanding balance (Debits - Credits)'
    )

    @api.depends('partner_id', 'payment_type', 'partner_type', 'state', 'amount')
    def _compute_partner_balance(self):
        """Calculate partner financial summary using accounting terminology"""
        for payment in self:
            # Reset all fields
            payment.partner_total_invoiced = 0.0
            payment.partner_total_credits = 0.0
            payment.partner_balance_due = 0.0

            if not payment.partner_id:
                continue

            try:
                # Customer payments (inbound)
                if payment.partner_type == 'customer' and payment.payment_type == 'inbound':

                    # Get invoices
                    invoices = self.env['account.move'].search([
                        ('partner_id', 'child_of', payment.partner_id.commercial_partner_id.id),
                        ('move_type', 'in', ['out_invoice', 'out_refund']),
                        ('state', '=', 'posted')
                    ])

                    out_invoices = invoices.filtered(lambda inv: inv.move_type == 'out_invoice')
                    out_refunds = invoices.filtered(lambda inv: inv.move_type == 'out_refund')

                    # Total Debits = All invoices
                    total_debits = sum(out_invoices.mapped('amount_total'))
                    payment.partner_total_invoiced = total_debits

                    # Get all customer payments
                    payments = self.env['account.payment'].search([
                        ('partner_id', 'child_of', payment.partner_id.commercial_partner_id.id),
                        ('partner_type', '=', 'customer'),
                        ('payment_type', '=', 'inbound'),
                        ('state', 'in', ['posted', 'paid'])
                    ])

                    total_payments = sum(payments.mapped('amount'))
                    total_credit_notes = sum(out_refunds.mapped('amount_total'))

                    # Total Credits = Payments + Credit Notes
                    payment.partner_total_credits = total_payments + total_credit_notes

                    # Due Amount = Debits - Credits
                    payment.partner_balance_due = total_debits - (total_payments + total_credit_notes)

                # Vendor payments (outbound)
                elif payment.partner_type == 'supplier' and payment.payment_type == 'outbound':

                    bills = self.env['account.move'].search([
                        ('partner_id', 'child_of', payment.partner_id.commercial_partner_id.id),
                        ('move_type', 'in', ['in_invoice', 'in_refund']),
                        ('state', '=', 'posted')
                    ])

                    in_invoices = bills.filtered(lambda bill: bill.move_type == 'in_invoice')
                    in_refunds = bills.filtered(lambda bill: bill.move_type == 'in_refund')

                    # Total Debits = All bills
                    total_debits = sum(in_invoices.mapped('amount_total'))
                    payment.partner_total_invoiced = total_debits

                    # Get all vendor payments
                    payments = self.env['account.payment'].search([
                        ('partner_id', 'child_of', payment.partner_id.commercial_partner_id.id),
                        ('partner_type', '=', 'supplier'),
                        ('payment_type', '=', 'outbound'),
                        ('state', 'in', ['posted', 'paid'])
                    ])

                    total_payments = sum(payments.mapped('amount'))
                    total_credit_notes = sum(in_refunds.mapped('amount_total'))

                    # Total Credits = Payments + Credit Notes
                    payment.partner_total_credits = total_payments + total_credit_notes

                    # Due Amount = Debits - Credits
                    payment.partner_balance_due = total_debits - (total_payments + total_credit_notes)

            except Exception as e:
                _logger.error(f"ERROR computing partner balance for {payment.partner_id.name}: {str(e)}", exc_info=True)
                payment.partner_total_invoiced = 0.0
                payment.partner_total_credits = 0.0
                payment.partner_balance_due = 0.0

    def action_view_invoices(self):
        """Open invoices/bills for the partner"""
        self.ensure_one()

        if not self.partner_id:
            raise UserError("No partner selected.")

        if self.partner_type == 'customer':
            move_types = ['out_invoice', 'out_refund']
            name = f'Invoices - {self.partner_id.name}'
        else:
            move_types = ['in_invoice', 'in_refund']
            name = f'Bills - {self.partner_id.name}'

        return {
            'name': name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],
            'domain': [
                ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
                ('move_type', 'in', move_types),
                ('state', '=', 'posted')
            ],
            'context': {'create': False},
        }

    def action_view_credits(self):
        """Open BOTH credit notes AND advance payments - credit entries only"""
        self.ensure_one()

        if not self.partner_id:
            raise UserError("No partner selected.")

        if self.partner_type == 'customer':
            move_types = ['out_refund', 'entry']
            name_prefix = 'Amount Received'
        else:
            move_types = ['in_refund', 'entry']
            name_prefix = 'Amount Paid'

        # Show only CREDIT entries (advance payments + credit notes)
        return {
            'name': f'{name_prefix} (Credit Notes & Advance Payments) - {self.partner_id.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],
            'domain': [
                ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
                ('move_id.state', '=', 'posted'),
                ('move_id.move_type', 'in', move_types),
                ('credit', '>', 0)
            ],
            'context': {'create': False},
        }

    def action_view_payments(self):
        """Open all payments for the partner"""
        self.ensure_one()

        if not self.partner_id:
            raise UserError("No partner selected.")

        return {
            'name': f'Payments - {self.partner_id.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],
            'domain': [
                ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
                ('partner_type', '=', self.partner_type),
                ('payment_type', '=', self.payment_type),
                ('state', 'in', ['posted', 'paid'])
            ],
            'context': {
                'create': False,
                'default_partner_id': self.partner_id.id,
                'default_partner_type': self.partner_type,
                'default_payment_type': self.payment_type,
            },
        }
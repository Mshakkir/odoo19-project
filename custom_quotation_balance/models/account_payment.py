from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    partner_total_invoiced = fields.Monetary(
        string='Total Invoiced/Billed',
        compute='_compute_partner_balance',
        currency_field='currency_id',
        help='Total invoiced or billed for this partner'
    )

    partner_total_paid = fields.Monetary(
        string='Amount Paid',
        compute='_compute_partner_balance',
        currency_field='currency_id',
        help='Total amount paid'
    )

    partner_balance_due = fields.Monetary(
        string='Balance Due',
        compute='_compute_partner_balance',
        currency_field='currency_id',
        help='Remaining balance'
    )

    @api.depends('partner_id', 'payment_type', 'partner_type', 'state', 'amount')
    def _compute_partner_balance(self):
        """Calculate partner financial summary"""
        for payment in self:
            # Reset all fields
            payment.partner_total_invoiced = 0.0
            payment.partner_total_paid = 0.0
            payment.partner_balance_due = 0.0

            if not payment.partner_id:
                continue

            _logger.info(f"=== Computing balance for payment {payment.name} ===")
            _logger.info(f"Partner: {payment.partner_id.name}")
            _logger.info(f"Partner Type: {payment.partner_type}")
            _logger.info(f"Payment Type: {payment.payment_type}")
            _logger.info(f"State: {payment.state}")
            _logger.info(f"Amount: {payment.amount}")

            try:
                # Customer payments (inbound)
                if payment.partner_type == 'customer' and payment.payment_type == 'inbound':
                    _logger.info("Processing CUSTOMER payment")

                    # Get invoices
                    invoices = self.env['account.move'].search([
                        ('partner_id', 'child_of', payment.partner_id.commercial_partner_id.id),
                        ('move_type', 'in', ['out_invoice', 'out_refund']),
                        ('state', '=', 'posted')
                    ])
                    _logger.info(f"Found {len(invoices)} invoices for customer")

                    total_invoiced = sum(invoices.filtered(
                        lambda inv: inv.move_type == 'out_invoice'
                    ).mapped('amount_total'))

                    total_refunded = sum(invoices.filtered(
                        lambda inv: inv.move_type == 'out_refund'
                    ).mapped('amount_total'))

                    total_residual = sum(invoices.mapped('amount_residual'))

                    payment.partner_total_invoiced = total_invoiced - total_refunded
                    payment.partner_balance_due = total_residual

                    _logger.info(f"Total Invoiced: {payment.partner_total_invoiced}")
                    _logger.info(f"Balance Due: {payment.partner_balance_due}")

                    # Get all customer payments (including direct payments)
                    payments = self.env['account.payment'].search([
                        ('partner_id', 'child_of', payment.partner_id.commercial_partner_id.id),
                        ('partner_type', '=', 'customer'),
                        ('payment_type', '=', 'inbound'),
                        ('state', '=', 'posted')
                    ])

                    _logger.info(f"Found {len(payments)} posted customer payments:")
                    for p in payments:
                        _logger.info(f"  - {p.name}: {p.amount} {p.currency_id.name} (State: {p.state})")

                    total_payments = sum(payments.mapped('amount'))
                    payment.partner_total_paid = total_payments

                    _logger.info(f"Total Payments: {payment.partner_total_paid}")

                # Vendor payments (outbound)
                elif payment.partner_type == 'supplier' and payment.payment_type == 'outbound':
                    _logger.info("Processing VENDOR payment")

                    bills = self.env['account.move'].search([
                        ('partner_id', 'child_of', payment.partner_id.commercial_partner_id.id),
                        ('move_type', 'in', ['in_invoice', 'in_refund']),
                        ('state', '=', 'posted')
                    ])
                    _logger.info(f"Found {len(bills)} bills for vendor")

                    total_billed = sum(bills.filtered(
                        lambda bill: bill.move_type == 'in_invoice'
                    ).mapped('amount_total'))

                    total_refunded = sum(bills.filtered(
                        lambda bill: bill.move_type == 'in_refund'
                    ).mapped('amount_total'))

                    total_residual = sum(bills.mapped('amount_residual'))

                    payment.partner_total_invoiced = total_billed - total_refunded
                    payment.partner_balance_due = total_residual

                    # Get all vendor payments (including direct payments)
                    payments = self.env['account.payment'].search([
                        ('partner_id', 'child_of', payment.partner_id.commercial_partner_id.id),
                        ('partner_type', '=', 'supplier'),
                        ('payment_type', '=', 'outbound'),
                        ('state', '=', 'posted')
                    ])

                    _logger.info(f"Found {len(payments)} posted vendor payments:")
                    for p in payments:
                        _logger.info(f"  - {p.name}: {p.amount} (State: {p.state})")

                    total_payments = sum(payments.mapped('amount'))
                    payment.partner_total_paid = total_payments

                    _logger.info(f"Total Payments: {payment.partner_total_paid}")

                else:
                    _logger.warning(
                        f"Unexpected payment configuration: partner_type={payment.partner_type}, payment_type={payment.payment_type}")

            except Exception as e:
                _logger.error(f"ERROR computing partner balance: {str(e)}", exc_info=True)
                payment.partner_total_invoiced = 0.0
                payment.partner_total_paid = 0.0
                payment.partner_balance_due = 0.0

    def action_view_partner_invoices(self):
        """Open partner invoices/bills based on payment type"""
        self.ensure_one()

        if not self.partner_id:
            raise UserError("No partner selected.")

        if self.partner_type == 'customer':
            # Customer invoices
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
        else:
            # Vendor bills
            return {
                'name': f'Bills - {self.partner_id.name}',
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'domain': [
                    ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
                    ('move_type', 'in', ['in_invoice', 'in_refund']),
                    ('state', '=', 'posted')
                ],
                'context': {'create': False},
            }

    def action_view_partner_payments(self):
        """Open all partner payments"""
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
                ('state', '=', 'posted')
            ],
            'context': {
                'create': False,
                'default_partner_id': self.partner_id.id,
                'default_partner_type': self.partner_type,
                'default_payment_type': self.payment_type,
            },
        }
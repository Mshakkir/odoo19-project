

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    # For Customer Invoices - Using Accounting Terminology
    customer_total_invoiced = fields.Monetary(
        string='Total Debits',
        compute='_compute_partner_balance',
        currency_field='currency_id',
        help='Total debits (invoices) for this customer'
    )

    customer_total_credits = fields.Monetary(
        string='Total Credits',
        compute='_compute_partner_balance',
        currency_field='currency_id',
        help='Total credits (payments + credit notes) received from customer'
    )

    customer_balance_due = fields.Monetary(
        string='Due Amount',
        compute='_compute_partner_balance',
        currency_field='currency_id',
        help='Outstanding balance (Debits - Credits)'
    )

    # For Vendor Bills - Using Accounting Terminology
    vendor_total_billed = fields.Monetary(
        string='Total Debits',
        compute='_compute_partner_balance',
        currency_field='currency_id',
        help='Total debits (bills) from this vendor'
    )

    vendor_total_credits = fields.Monetary(
        string='Total Credits',
        compute='_compute_partner_balance',
        currency_field='currency_id',
        help='Total credits (payments + credit notes) to vendor'
    )

    vendor_balance_due = fields.Monetary(
        string='Due Amount',
        compute='_compute_partner_balance',
        currency_field='currency_id',
        help='Outstanding balance (Debits - Credits)'
    )

    @api.depends('partner_id', 'move_type', 'state')
    def _compute_partner_balance(self):
        """Calculate partner financial summary using accounting terminology"""
        for move in self:
            # Reset all fields first
            move.customer_total_invoiced = 0.0
            move.customer_total_credits = 0.0
            move.customer_balance_due = 0.0
            move.vendor_total_billed = 0.0
            move.vendor_total_credits = 0.0
            move.vendor_balance_due = 0.0

            if not move.partner_id or move.move_type not in ['out_invoice', 'out_refund', 'in_invoice', 'in_refund']:
                continue

            try:
                # Customer invoices
                if move.move_type in ['out_invoice', 'out_refund']:
                    invoices = self.env['account.move'].search([
                        ('partner_id', 'child_of', move.partner_id.commercial_partner_id.id),
                        ('move_type', 'in', ['out_invoice', 'out_refund']),
                        ('state', '=', 'posted')
                    ])

                    # Separate invoices and credit notes
                    out_invoices = invoices.filtered(lambda inv: inv.move_type == 'out_invoice')
                    out_refunds = invoices.filtered(lambda inv: inv.move_type == 'out_refund')

                    # Total Debits = All invoices
                    total_debits = sum(out_invoices.mapped('amount_total'))
                    move.customer_total_invoiced = total_debits

                    # Get all customer payments
                    payments = self.env['account.payment'].search([
                        ('partner_id', 'child_of', move.partner_id.commercial_partner_id.id),
                        ('partner_type', '=', 'customer'),
                        ('payment_type', '=', 'inbound'),
                        ('state', 'in', ['posted', 'paid'])
                    ])

                    total_payments = sum(payments.mapped('amount'))
                    total_credit_notes = sum(out_refunds.mapped('amount_total'))

                    # Total Credits = Payments + Credit Notes
                    move.customer_total_credits = total_payments + total_credit_notes

                    # Due Amount = Debits - Credits
                    move.customer_balance_due = total_debits - (total_payments + total_credit_notes)

                # Vendor bills
                elif move.move_type in ['in_invoice', 'in_refund']:
                    bills = self.env['account.move'].search([
                        ('partner_id', 'child_of', move.partner_id.commercial_partner_id.id),
                        ('move_type', 'in', ['in_invoice', 'in_refund']),
                        ('state', '=', 'posted')
                    ])

                    # Separate bills and credit notes
                    in_invoices = bills.filtered(lambda bill: bill.move_type == 'in_invoice')
                    in_refunds = bills.filtered(lambda bill: bill.move_type == 'in_refund')

                    # Total Debits = All bills
                    total_debits = sum(in_invoices.mapped('amount_total'))
                    move.vendor_total_billed = total_debits

                    # Get all vendor payments
                    payments = self.env['account.payment'].search([
                        ('partner_id', 'child_of', move.partner_id.commercial_partner_id.id),
                        ('partner_type', '=', 'supplier'),
                        ('payment_type', '=', 'outbound'),
                        ('state', 'in', ['posted', 'paid'])
                    ])

                    total_payments = sum(payments.mapped('amount'))
                    total_credit_notes = sum(in_refunds.mapped('amount_total'))

                    # Total Credits = Payments + Credit Notes
                    move.vendor_total_credits = total_payments + total_credit_notes

                    # Due Amount = Debits - Credits
                    move.vendor_balance_due = total_debits - (total_payments + total_credit_notes)

            except Exception as e:
                _logger.error(f"ERROR computing partner balance for {move.partner_id.name}: {str(e)}", exc_info=True)
                move.customer_total_invoiced = 0.0
                move.customer_total_credits = 0.0
                move.customer_balance_due = 0.0
                move.vendor_total_billed = 0.0
                move.vendor_total_credits = 0.0
                move.vendor_balance_due = 0.0

    def action_view_customer_invoices(self):
        """Open all customer invoices"""
        self.ensure_one()

        if not self.partner_id:
            raise UserError("No customer selected.")

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
            raise UserError("No customer selected.")

        # Shows only CREDIT entries (advance payments + credit notes)
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
        """Open customer payments"""
        self.ensure_one()

        if not self.partner_id:
            raise UserError("No customer selected.")

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

    def action_view_vendor_bills(self):
        """Open all vendor bills"""
        self.ensure_one()

        if not self.partner_id:
            raise UserError("No vendor selected.")

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

    def action_view_vendor_credits(self):
        """Open BOTH credit notes AND advance payments - credit entries only"""
        self.ensure_one()

        if not self.partner_id:
            raise UserError("No vendor selected.")

        # Shows only CREDIT entries (advance payments + credit notes)
        return {
            'name': f'Amount Paid (Credit Notes & Advance Payments) - {self.partner_id.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],
            'domain': [
                ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
                ('move_id.state', '=', 'posted'),
                ('move_id.move_type', 'in', ['in_refund', 'entry']),
                ('credit', '>', 0)
            ],
            'context': {'create': False},
        }

    def action_view_vendor_payments(self):
        """Open vendor payments"""
        self.ensure_one()

        if not self.partner_id:
            raise UserError("No vendor selected.")

        return {
            'name': f'Payments - {self.partner_id.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],
            'domain': [
                ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
                ('partner_type', '=', 'supplier'),
                ('payment_type', '=', 'outbound'),
                ('state', 'in', ['posted', 'paid'])
            ],
            'context': {
                'create': False,
                'default_partner_id': self.partner_id.id,
                'default_partner_type': 'supplier',
                'default_payment_type': 'outbound',
            },
        }
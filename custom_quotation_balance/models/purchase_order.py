
from odoo import models, fields, api
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # Vendor Balance - Using Accounting Terminology
    vendor_total_billed = fields.Monetary(
        string='Total Debits',
        compute='_compute_vendor_balance',
        currency_field='currency_id',
        help='Total debits (bills) from this vendor'
    )

    vendor_total_credits = fields.Monetary(
        string='Total Credits',
        compute='_compute_vendor_balance',
        currency_field='currency_id',
        help='Total credits (payments + credit notes) to vendor'
    )

    vendor_balance_due = fields.Monetary(
        string='Due Amount',
        compute='_compute_vendor_balance',
        currency_field='currency_id',
        help='Outstanding balance (Debits - Credits)'
    )

    @api.depends('partner_id')
    def _compute_vendor_balance(self):
        """Calculate vendor financial summary using accounting terminology"""
        for order in self:
            if order.partner_id:
                try:
                    if 'account.move' not in self.env:
                        order.vendor_total_billed = 0.0
                        order.vendor_total_credits = 0.0
                        order.vendor_balance_due = 0.0
                        continue

                    # Get all vendor bills and credit notes
                    bills = self.env['account.move'].search([
                        ('partner_id', 'child_of', order.partner_id.commercial_partner_id.id),
                        ('move_type', 'in', ['in_invoice', 'in_refund']),
                        ('state', '=', 'posted')
                    ])

                    # Separate bills and credit notes
                    in_invoices = bills.filtered(lambda bill: bill.move_type == 'in_invoice')
                    in_refunds = bills.filtered(lambda bill: bill.move_type == 'in_refund')

                    # Total Debits = All bills
                    total_debits = sum(in_invoices.mapped('amount_total'))
                    order.vendor_total_billed = total_debits

                    # Get all vendor payments
                    payments = self.env['account.payment'].search([
                        ('partner_id', 'child_of', order.partner_id.commercial_partner_id.id),
                        ('partner_type', '=', 'supplier'),
                        ('payment_type', '=', 'outbound'),
                        ('state', 'in', ['posted', 'paid'])
                    ])

                    total_payments = sum(payments.mapped('amount'))
                    total_credit_notes = sum(in_refunds.mapped('amount_total'))

                    # Total Credits = Payments + Credit Notes
                    order.vendor_total_credits = total_payments + total_credit_notes

                    # Due Amount = Debits - Credits
                    order.vendor_balance_due = total_debits - (total_payments + total_credit_notes)

                except Exception as e:
                    order.vendor_total_billed = 0.0
                    order.vendor_total_credits = 0.0
                    order.vendor_balance_due = 0.0
            else:
                order.vendor_total_billed = 0.0
                order.vendor_total_credits = 0.0
                order.vendor_balance_due = 0.0

    def action_view_vendor_bills(self):
        """Open filtered list of vendor bills"""
        self.ensure_one()

        if not self.partner_id:
            raise UserError("Please select a vendor first.")

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
            raise UserError("Please select a vendor first.")

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
        """Open filtered list of vendor payments"""
        self.ensure_one()

        if not self.partner_id:
            raise UserError("Please select a vendor first.")

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
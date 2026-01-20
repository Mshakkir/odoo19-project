# from odoo import models, fields, api
# from odoo.exceptions import UserError
#
#
# class AccountPayment(models.Model):
#     _inherit = 'account.payment'
#
#     partner_total_invoiced = fields.Monetary(
#         string='Total Invoiced/Billed',
#         compute='_compute_partner_balance',
#         currency_field='currency_id',
#         help='Total invoiced or billed for this partner'
#     )
#
#     partner_total_paid = fields.Monetary(
#         string='Amount Paid',
#         compute='_compute_partner_balance',
#         currency_field='currency_id',
#         help='Total amount paid'
#     )
#
#     partner_balance_due = fields.Monetary(
#         string='Balance Due',
#         compute='_compute_partner_balance',
#         currency_field='currency_id',
#         help='Remaining balance'
#     )
#
#     @api.depends('partner_id', 'payment_type')
#     def _compute_partner_balance(self):
#         """Calculate partner financial summary"""
#         for payment in self:
#             if payment.partner_id:
#                 try:
#                     # Customer payments (inbound)
#                     if payment.payment_type == 'inbound':
#                         invoices = self.env['account.move'].search([
#                             ('partner_id', 'child_of', payment.partner_id.commercial_partner_id.id),
#                             ('move_type', 'in', ['out_invoice', 'out_refund']),
#                             ('state', '=', 'posted')
#                         ])
#
#                         total_invoiced = sum(invoices.filtered(
#                             lambda inv: inv.move_type == 'out_invoice'
#                         ).mapped('amount_total'))
#
#                         total_refunded = sum(invoices.filtered(
#                             lambda inv: inv.move_type == 'out_refund'
#                         ).mapped('amount_total'))
#
#                         total_residual = sum(invoices.mapped('amount_residual'))
#
#                         payment.partner_total_invoiced = total_invoiced - total_refunded
#                         payment.partner_balance_due = total_residual
#                         payment.partner_total_paid = payment.partner_total_invoiced - payment.partner_balance_due
#
#                     # Vendor payments (outbound)
#                     elif payment.payment_type == 'outbound':
#                         bills = self.env['account.move'].search([
#                             ('partner_id', 'child_of', payment.partner_id.commercial_partner_id.id),
#                             ('move_type', 'in', ['in_invoice', 'in_refund']),
#                             ('state', '=', 'posted')
#                         ])
#
#                         total_billed = sum(bills.filtered(
#                             lambda bill: bill.move_type == 'in_invoice'
#                         ).mapped('amount_total'))
#
#                         total_refunded = sum(bills.filtered(
#                             lambda bill: bill.move_type == 'in_refund'
#                         ).mapped('amount_total'))
#
#                         total_residual = sum(bills.mapped('amount_residual'))
#
#                         payment.partner_total_invoiced = total_billed - total_refunded
#                         payment.partner_balance_due = total_residual
#                         payment.partner_total_paid = payment.partner_total_invoiced - payment.partner_balance_due
#                     else:
#                         payment.partner_total_invoiced = 0.0
#                         payment.partner_total_paid = 0.0
#                         payment.partner_balance_due = 0.0
#
#                 except Exception:
#                     payment.partner_total_invoiced = 0.0
#                     payment.partner_total_paid = 0.0
#                     payment.partner_balance_due = 0.0
#             else:
#                 payment.partner_total_invoiced = 0.0
#                 payment.partner_total_paid = 0.0
#                 payment.partner_balance_due = 0.0
#
#     def action_view_partner_invoices(self):
#         """Open partner invoices/bills based on payment type"""
#         self.ensure_one()
#
#         if not self.partner_id:
#             raise UserError("No partner selected.")
#
#         if self.payment_type == 'inbound':
#             # Customer invoices
#             return {
#                 'name': f'Invoices - {self.partner_id.name}',
#                 'type': 'ir.actions.act_window',
#                 'res_model': 'account.move',
#                 'view_mode': 'list,form',
#                 'views': [(False, 'list'), (False, 'form')],
#                 'domain': [
#                     ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
#                     ('move_type', 'in', ['out_invoice', 'out_refund']),
#                     ('state', '=', 'posted')
#                 ],
#                 'context': {'create': False},
#             }
#         else:
#             # Vendor bills
#             return {
#                 'name': f'Bills - {self.partner_id.name}',
#                 'type': 'ir.actions.act_window',
#                 'res_model': 'account.move',
#                 'view_mode': 'list,form',
#                 'views': [(False, 'list'), (False, 'form')],
#                 'domain': [
#                     ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
#                     ('move_type', 'in', ['in_invoice', 'in_refund']),
#                     ('state', '=', 'posted')
#                 ],
#                 'context': {'create': False},
#             }
#
#     def action_view_partner_payments(self):
#         """Open all partner payments"""
#         self.ensure_one()
#
#         if not self.partner_id:
#             raise UserError("No partner selected.")
#
#         return {
#             'name': f'Payments - {self.partner_id.name}',
#             'type': 'ir.actions.act_window',
#             'res_model': 'account.payment',
#             'view_mode': 'list,form',
#             'views': [(False, 'list'), (False, 'form')],
#             'domain': [
#                 ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
#                 ('payment_type', '=', self.payment_type),
#             ],
#             'context': {
#                 'create': False,
#                 'default_partner_id': self.partner_id.id,
#                 'default_payment_type': self.payment_type,
#             },
#         }

from odoo import models, fields, api
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    # For Customer Invoices
    customer_total_invoiced = fields.Monetary(
        string='Total Invoiced',
        compute='_compute_partner_balance',
        currency_field='currency_id',
        help='Total invoiced for this customer'
    )

    customer_total_paid = fields.Monetary(
        string='Amount Paid',
        compute='_compute_partner_balance',
        currency_field='currency_id',
        help='Total amount paid by this customer'
    )

    customer_balance_due = fields.Monetary(
        string='Balance Due',
        compute='_compute_partner_balance',
        currency_field='currency_id',
        help='Remaining balance for this customer'
    )

    # For Vendor Bills
    vendor_total_billed = fields.Monetary(
        string='Total Billed',
        compute='_compute_partner_balance',
        currency_field='currency_id',
        help='Total billed from this vendor'
    )

    vendor_total_paid = fields.Monetary(
        string='Amount Paid',
        compute='_compute_partner_balance',
        currency_field='currency_id',
        help='Total amount paid to this vendor'
    )

    vendor_balance_due = fields.Monetary(
        string='Balance Due',
        compute='_compute_partner_balance',
        currency_field='currency_id',
        help='Remaining balance for this vendor'
    )

    @api.depends('partner_id', 'move_type')
    def _compute_partner_balance(self):
        """Calculate partner financial summary based on invoice type"""
        for move in self:
            if move.partner_id and move.move_type in ['out_invoice', 'out_refund', 'in_invoice', 'in_refund']:
                try:
                    # Customer invoices
                    if move.move_type in ['out_invoice', 'out_refund']:
                        invoices = self.env['account.move'].search([
                            ('partner_id', 'child_of', move.partner_id.commercial_partner_id.id),
                            ('move_type', 'in', ['out_invoice', 'out_refund']),
                            ('state', '=', 'posted')
                        ])

                        total_invoiced = 0.0
                        total_residual = 0.0

                        for inv in invoices:
                            if inv.move_type == 'out_invoice':
                                # Regular invoice - add to total
                                total_invoiced += inv.amount_total
                                total_residual += inv.amount_residual
                            else:  # out_refund
                                # Credit note - subtract from total
                                total_invoiced -= inv.amount_total
                                total_residual -= inv.amount_residual

                        move.customer_total_invoiced = total_invoiced
                        move.customer_balance_due = total_residual
                        move.customer_total_paid = move.customer_total_invoiced - move.customer_balance_due

                        # Set vendor fields to 0 for customer invoices
                        move.vendor_total_billed = 0.0
                        move.vendor_total_paid = 0.0
                        move.vendor_balance_due = 0.0

                    # Vendor bills
                    elif move.move_type in ['in_invoice', 'in_refund']:
                        bills = self.env['account.move'].search([
                            ('partner_id', 'child_of', move.partner_id.commercial_partner_id.id),
                            ('move_type', 'in', ['in_invoice', 'in_refund']),
                            ('state', '=', 'posted')
                        ])

                        total_billed = 0.0
                        total_residual = 0.0

                        for bill in bills:
                            if bill.move_type == 'in_invoice':
                                # Regular bill - add to total
                                total_billed += bill.amount_total
                                total_residual += bill.amount_residual
                            else:  # in_refund
                                # Vendor credit note - subtract from total
                                total_billed -= bill.amount_total
                                total_residual -= bill.amount_residual

                        move.vendor_total_billed = total_billed
                        move.vendor_balance_due = total_residual
                        move.vendor_total_paid = move.vendor_total_billed - move.vendor_balance_due

                        # Set customer fields to 0 for vendor bills
                        move.customer_total_invoiced = 0.0
                        move.customer_total_paid = 0.0
                        move.customer_balance_due = 0.0

                except Exception:
                    move.customer_total_invoiced = 0.0
                    move.customer_total_paid = 0.0
                    move.customer_balance_due = 0.0
                    move.vendor_total_billed = 0.0
                    move.vendor_total_paid = 0.0
                    move.vendor_balance_due = 0.0
            else:
                move.customer_total_invoiced = 0.0
                move.customer_total_paid = 0.0
                move.customer_balance_due = 0.0
                move.vendor_total_billed = 0.0
                move.vendor_total_paid = 0.0
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

    def action_view_customer_payments(self):
        """Open customer payments"""
        self.ensure_one()

        if not self.partner_id:
            raise UserError("No customer selected.")

        all_payments = self.env['account.payment'].search([
            ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
        ])

        if not all_payments:
            return {
                'name': f'Paid Invoices - {self.partner_id.name}',
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'domain': [
                    ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
                    ('payment_state', 'in', ['paid', 'in_payment', 'partial']),
                    ('state', '=', 'posted'),
                ],
                'context': {'create': False},
            }

        return {
            'name': f'Payments - {self.partner_id.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],
            'domain': [
                ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
                ('payment_type', '=', 'inbound'),
            ],
            'context': {
                'create': False,
                'default_partner_id': self.partner_id.id,
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

    def action_view_vendor_payments(self):
        """Open vendor payments"""
        self.ensure_one()

        if not self.partner_id:
            raise UserError("No vendor selected.")

        all_payments = self.env['account.payment'].search([
            ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
        ])

        if not all_payments:
            return {
                'name': f'Paid Bills - {self.partner_id.name}',
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'domain': [
                    ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
                    ('payment_state', 'in', ['paid', 'in_payment', 'partial']),
                    ('state', '=', 'posted'),
                ],
                'context': {'create': False},
            }

        return {
            'name': f'Payments - {self.partner_id.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],
            'domain': [
                ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
                ('payment_type', '=', 'outbound'),
            ],
            'context': {
                'create': False,
                'default_partner_id': self.partner_id.id,
                'default_payment_type': 'outbound',
            },
        }
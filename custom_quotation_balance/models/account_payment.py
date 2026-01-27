# # from odoo import models, fields, api
# # from odoo.exceptions import UserError
# # import logging
# #
# # _logger = logging.getLogger(__name__)
# #
# #
# # class AccountPayment(models.Model):
# #     _inherit = 'account.payment'
# #
# #     partner_total_invoiced = fields.Monetary(
# #         string='Total Invoiced/Billed',
# #         compute='_compute_partner_balance',
# #         currency_field='currency_id',
# #         help='Total invoiced or billed for this partner'
# #     )
# #
# #     partner_total_paid = fields.Monetary(
# #         string='Amount Paid',
# #         compute='_compute_partner_balance',
# #         currency_field='currency_id',
# #         help='Total amount paid'
# #     )
# #
# #     partner_balance_due = fields.Monetary(
# #         string='Balance Due',
# #         compute='_compute_partner_balance',
# #         currency_field='currency_id',
# #         help='Remaining balance'
# #     )
# #
# #     @api.depends('partner_id', 'payment_type', 'partner_type', 'state', 'amount')
# #     def _compute_partner_balance(self):
# #         """Calculate partner financial summary"""
# #         for payment in self:
# #             # Reset all fields
# #             payment.partner_total_invoiced = 0.0
# #             payment.partner_total_paid = 0.0
# #             payment.partner_balance_due = 0.0
# #
# #             if not payment.partner_id:
# #                 continue
# #
# #             try:
# #                 # Customer payments (inbound)
# #                 if payment.partner_type == 'customer' and payment.payment_type == 'inbound':
# #
# #                     # Get invoices
# #                     invoices = self.env['account.move'].search([
# #                         ('partner_id', 'child_of', payment.partner_id.commercial_partner_id.id),
# #                         ('move_type', 'in', ['out_invoice', 'out_refund']),
# #                         ('state', '=', 'posted')
# #                     ])
# #
# #                     total_invoiced = sum(invoices.filtered(
# #                         lambda inv: inv.move_type == 'out_invoice'
# #                     ).mapped('amount_total'))
# #
# #                     total_refunded = sum(invoices.filtered(
# #                         lambda inv: inv.move_type == 'out_refund'
# #                     ).mapped('amount_total'))
# #
# #                     total_residual = sum(invoices.mapped('amount_residual'))
# #
# #                     payment.partner_total_invoiced = total_invoiced - total_refunded
# #                     payment.partner_balance_due = total_residual
# #
# #                     # Get all customer payments (including direct payments)
# #                     # FIXED: Include both 'posted' and 'paid' states
# #                     payments = self.env['account.payment'].search([
# #                         ('partner_id', 'child_of', payment.partner_id.commercial_partner_id.id),
# #                         ('partner_type', '=', 'customer'),
# #                         ('payment_type', '=', 'inbound'),
# #                         ('state', 'in', ['posted', 'paid'])  # ← THIS IS THE FIX
# #                     ])
# #
# #                     total_payments = sum(payments.mapped('amount'))
# #                     payment.partner_total_paid = total_payments
# #
# #                 # Vendor payments (outbound)
# #                 elif payment.partner_type == 'supplier' and payment.payment_type == 'outbound':
# #
# #                     bills = self.env['account.move'].search([
# #                         ('partner_id', 'child_of', payment.partner_id.commercial_partner_id.id),
# #                         ('move_type', 'in', ['in_invoice', 'in_refund']),
# #                         ('state', '=', 'posted')
# #                     ])
# #
# #                     total_billed = sum(bills.filtered(
# #                         lambda bill: bill.move_type == 'in_invoice'
# #                     ).mapped('amount_total'))
# #
# #                     total_refunded = sum(bills.filtered(
# #                         lambda bill: bill.move_type == 'in_refund'
# #                     ).mapped('amount_total'))
# #
# #                     total_residual = sum(bills.mapped('amount_residual'))
# #
# #                     payment.partner_total_invoiced = total_billed - total_refunded
# #                     payment.partner_balance_due = total_residual
# #
# #                     # Get all vendor payments (including direct payments)
# #                     # FIXED: Include both 'posted' and 'paid' states
# #                     payments = self.env['account.payment'].search([
# #                         ('partner_id', 'child_of', payment.partner_id.commercial_partner_id.id),
# #                         ('partner_type', '=', 'supplier'),
# #                         ('payment_type', '=', 'outbound'),
# #                         ('state', 'in', ['posted', 'paid'])  # ← THIS IS THE FIX
# #                     ])
# #
# #                     total_payments = sum(payments.mapped('amount'))
# #                     payment.partner_total_paid = total_payments
# #
# #                 else:
# #                     payment.partner_total_invoiced = 0.0
# #                     payment.partner_total_paid = 0.0
# #                     payment.partner_balance_due = 0.0
# #
# #             except Exception as e:
# #                 _logger.error(f"ERROR computing partner balance: {str(e)}", exc_info=True)
# #                 payment.partner_total_invoiced = 0.0
# #                 payment.partner_total_paid = 0.0
# #                 payment.partner_balance_due = 0.0
# #
# #     def action_view_partner_invoices(self):
# #         """Open partner invoices/bills based on payment type"""
# #         self.ensure_one()
# #
# #         if not self.partner_id:
# #             raise UserError("No partner selected.")
# #
# #         if self.partner_type == 'customer':
# #             # Customer invoices
# #             return {
# #                 'name': f'Invoices - {self.partner_id.name}',
# #                 'type': 'ir.actions.act_window',
# #                 'res_model': 'account.move',
# #                 'view_mode': 'list,form',
# #                 'views': [(False, 'list'), (False, 'form')],
# #                 'domain': [
# #                     ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
# #                     ('move_type', 'in', ['out_invoice', 'out_refund']),
# #                     ('state', '=', 'posted')
# #                 ],
# #                 'context': {'create': False},
# #             }
# #         else:
# #             # Vendor bills
# #             return {
# #                 'name': f'Bills - {self.partner_id.name}',
# #                 'type': 'ir.actions.act_window',
# #                 'res_model': 'account.move',
# #                 'view_mode': 'list,form',
# #                 'views': [(False, 'list'), (False, 'form')],
# #                 'domain': [
# #                     ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
# #                     ('move_type', 'in', ['in_invoice', 'in_refund']),
# #                     ('state', '=', 'posted')
# #                 ],
# #                 'context': {'create': False},
# #             }
# #
# #     def action_view_partner_payments(self):
# #         """Open all partner payments"""
# #         self.ensure_one()
# #
# #         if not self.partner_id:
# #             raise UserError("No partner selected.")
# #
# #         return {
# #             'name': f'Payments - {self.partner_id.name}',
# #             'type': 'ir.actions.act_window',
# #             'res_model': 'account.payment',
# #             'view_mode': 'list,form',
# #             'views': [(False, 'list'), (False, 'form')],
# #             'domain': [
# #                 ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
# #                 ('partner_type', '=', self.partner_type),
# #                 ('payment_type', '=', self.payment_type),
# #                 ('state', 'in', ['posted', 'paid'])  # ← ALSO FIX HERE
# #             ],
# #             'context': {
# #                 'create': False,
# #                 'default_partner_id': self.partner_id.id,
# #                 'default_partner_type': self.partner_type,
# #                 'default_payment_type': self.payment_type,
# #             },
# #         }
#
# from odoo import models, fields, api
# from odoo.exceptions import UserError
# import logging
#
# _logger = logging.getLogger(__name__)
#
#
# class AccountPayment(models.Model):
#     _inherit = 'account.payment'
#
#     # Partner Balance - 4 FIELDS
#     partner_total_invoiced = fields.Monetary(
#         string='Total Invoiced/Billed',
#         compute='_compute_partner_balance',
#         currency_field='currency_id',
#         help='Total invoiced or billed for this partner'
#     )
#
#     partner_total_credits = fields.Monetary(
#         string='Total Credits',
#         compute='_compute_partner_balance',
#         currency_field='currency_id',
#         help='Total credit notes'
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
#         help='Current receivable/payable balance'
#     )
#
#     @api.depends('partner_id', 'payment_type', 'partner_type', 'state', 'amount')
#     def _compute_partner_balance(self):
#         """
#         Calculate partner financial summary - RESIDUAL METHOD
#         For payments, show current receivable/payable position
#         """
#         for payment in self:
#             # Reset all fields
#             payment.partner_total_invoiced = 0.0
#             payment.partner_total_credits = 0.0
#             payment.partner_total_paid = 0.0
#             payment.partner_balance_due = 0.0
#
#             if not payment.partner_id:
#                 continue
#
#             try:
#                 # Customer payments (inbound)
#                 if payment.partner_type == 'customer' and payment.payment_type == 'inbound':
#
#                     # Get invoices
#                     invoices = self.env['account.move'].search([
#                         ('partner_id', 'child_of', payment.partner_id.commercial_partner_id.id),
#                         ('move_type', 'in', ['out_invoice', 'out_refund']),
#                         ('state', '=', 'posted')
#                     ])
#
#                     out_invoices = invoices.filtered(lambda inv: inv.move_type == 'out_invoice')
#                     out_refunds = invoices.filtered(lambda inv: inv.move_type == 'out_refund')
#
#                     total_invoiced = sum(out_invoices.mapped('amount_total'))
#                     total_credits = sum(out_refunds.mapped('amount_total'))
#
#                     # RESIDUAL-BASED calculation
#                     invoice_residual = sum(out_invoices.mapped('amount_residual'))
#                     refund_residual = sum(out_refunds.mapped('amount_residual'))
#
#                     payment.partner_total_invoiced = total_invoiced
#                     payment.partner_total_credits = total_credits
#                     payment.partner_balance_due = invoice_residual - refund_residual
#
#                     # Get all customer payments
#                     payments = self.env['account.payment'].search([
#                         ('partner_id', 'child_of', payment.partner_id.commercial_partner_id.id),
#                         ('partner_type', '=', 'customer'),
#                         ('payment_type', '=', 'inbound'),
#                         ('state', 'in', ['posted', 'paid'])
#                     ])
#
#                     total_payments = sum(payments.mapped('amount'))
#                     payment.partner_total_paid = total_payments
#
#                 # Vendor payments (outbound)
#                 elif payment.partner_type == 'supplier' and payment.payment_type == 'outbound':
#
#                     bills = self.env['account.move'].search([
#                         ('partner_id', 'child_of', payment.partner_id.commercial_partner_id.id),
#                         ('move_type', 'in', ['in_invoice', 'in_refund']),
#                         ('state', '=', 'posted')
#                     ])
#
#                     in_invoices = bills.filtered(lambda bill: bill.move_type == 'in_invoice')
#                     in_refunds = bills.filtered(lambda bill: bill.move_type == 'in_refund')
#
#                     total_billed = sum(in_invoices.mapped('amount_total'))
#                     total_credits = sum(in_refunds.mapped('amount_total'))
#
#                     # RESIDUAL-BASED calculation
#                     bill_residual = sum(in_invoices.mapped('amount_residual'))
#                     refund_residual = sum(in_refunds.mapped('amount_residual'))
#
#                     payment.partner_total_invoiced = total_billed
#                     payment.partner_total_credits = total_credits
#                     payment.partner_balance_due = bill_residual - refund_residual
#
#                     # Get all vendor payments
#                     payments = self.env['account.payment'].search([
#                         ('partner_id', 'child_of', payment.partner_id.commercial_partner_id.id),
#                         ('partner_type', '=', 'supplier'),
#                         ('payment_type', '=', 'outbound'),
#                         ('state', 'in', ['posted', 'paid'])
#                     ])
#
#                     total_payments = sum(payments.mapped('amount'))
#                     payment.partner_total_paid = total_payments
#
#             except Exception as e:
#                 _logger.error(f"ERROR computing partner balance: {str(e)}", exc_info=True)
#                 payment.partner_total_invoiced = 0.0
#                 payment.partner_total_credits = 0.0
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
#         if self.partner_type == 'customer':
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
#     def action_view_partner_credits(self):
#         """Open partner credit notes"""
#         self.ensure_one()
#
#         if not self.partner_id:
#             raise UserError("No partner selected.")
#
#         if self.partner_type == 'customer':
#             move_type = 'out_refund'
#             title = 'Credit Notes'
#         else:
#             move_type = 'in_refund'
#             title = 'Credit Notes'
#
#         return {
#             'name': f'{title} - {self.partner_id.name}',
#             'type': 'ir.actions.act_window',
#             'res_model': 'account.move',
#             'view_mode': 'list,form',
#             'views': [(False, 'list'), (False, 'form')],
#             'domain': [
#                 ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
#                 ('move_type', '=', move_type),
#                 ('state', '=', 'posted')
#             ],
#             'context': {'create': False},
#         }
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
#                 ('partner_type', '=', self.partner_type),
#                 ('payment_type', '=', self.payment_type),
#                 ('state', 'in', ['posted', 'paid'])
#             ],
#             'context': {
#                 'create': False,
#                 'default_partner_id': self.partner_id.id,
#                 'default_partner_type': self.partner_type,
#                 'default_payment_type': self.payment_type,
#             },
#         }

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
        """Open credit notes for the partner"""
        self.ensure_one()

        if not self.partner_id:
            raise UserError("No partner selected.")

        if self.partner_type == 'customer':
            move_type = 'out_refund'
        else:
            move_type = 'in_refund'

        return {
            'name': f'Credit Notes - {self.partner_id.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],
            'domain': [
                ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
                ('move_type', '=', move_type),
                ('state', '=', 'posted')
            ],
            'context': {'create': False},
        }

    def action_view_credits_and_payments(self):
        """Open BOTH credit notes AND payments together"""
        self.ensure_one()

        if not self.partner_id:
            raise UserError("No partner selected.")

        if self.partner_type == 'customer':
            move_type = 'out_refund'
            name_prefix = 'Amount Received'
        else:
            move_type = 'in_refund'
            name_prefix = 'Amount Paid'

        return {
            'name': f'{name_prefix} (Credit Notes & Payments) - {self.partner_id.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],
            'domain': [
                ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
                ('move_type', '=', move_type),
                ('state', '=', 'posted')
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
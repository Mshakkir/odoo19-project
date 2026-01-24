# from odoo import models, fields, api
# from odoo.exceptions import UserError
# import logging
#
# _logger = logging.getLogger(__name__)
#
#
# class AccountMove(models.Model):
#     _inherit = 'account.move'
#
#     # For Customer Invoices
#     customer_total_invoiced = fields.Monetary(
#         string='Total Invoiced',
#         compute='_compute_partner_balance',
#         currency_field='currency_id',
#         help='Total invoiced for this customer'
#     )
#
#     customer_total_paid = fields.Monetary(
#         string='Amount Paid',
#         compute='_compute_partner_balance',
#         currency_field='currency_id',
#         help='Total amount paid by this customer'
#     )
#
#     customer_balance_due = fields.Monetary(
#         string='Balance Due',
#         compute='_compute_partner_balance',
#         currency_field='currency_id',
#         help='Remaining balance for this customer'
#     )
#
#     # For Vendor Bills
#     vendor_total_billed = fields.Monetary(
#         string='Total Billed',
#         compute='_compute_partner_balance',
#         currency_field='currency_id',
#         help='Total billed from this vendor'
#     )
#
#     vendor_total_paid = fields.Monetary(
#         string='Amount Paid',
#         compute='_compute_partner_balance',
#         currency_field='currency_id',
#         help='Total amount paid to this vendor'
#     )
#
#     vendor_balance_due = fields.Monetary(
#         string='Balance Due',
#         compute='_compute_partner_balance',
#         currency_field='currency_id',
#         help='Remaining balance for this vendor'
#     )
#
#     @api.depends('partner_id', 'move_type', 'state')
#     def _compute_partner_balance(self):
#         """Calculate partner financial summary based on invoice type"""
#         for move in self:
#             # Reset all fields first
#             move.customer_total_invoiced = 0.0
#             move.customer_total_paid = 0.0
#             move.customer_balance_due = 0.0
#             move.vendor_total_billed = 0.0
#             move.vendor_total_paid = 0.0
#             move.vendor_balance_due = 0.0
#
#             if not move.partner_id or move.move_type not in ['out_invoice', 'out_refund', 'in_invoice', 'in_refund']:
#                 continue
#
#             try:
#                 # Customer invoices
#                 if move.move_type in ['out_invoice', 'out_refund']:
#                     invoices = self.env['account.move'].search([
#                         ('partner_id', 'child_of', move.partner_id.commercial_partner_id.id),
#                         ('move_type', 'in', ['out_invoice', 'out_refund']),
#                         ('state', '=', 'posted')
#                     ])
#
#                     # Separate invoices and refunds
#                     out_invoices = invoices.filtered(lambda inv: inv.move_type == 'out_invoice')
#                     out_refunds = invoices.filtered(lambda inv: inv.move_type == 'out_refund')
#
#                     total_invoiced = sum(out_invoices.mapped('amount_total'))
#                     total_refunded = sum(out_refunds.mapped('amount_total'))
#
#                     # Calculate residual separately for invoices and refunds
#                     invoice_residual = sum(out_invoices.mapped('amount_residual'))
#                     refund_residual = sum(out_refunds.mapped('amount_residual'))
#
#                     move.customer_total_invoiced = total_invoiced - total_refunded
#                     move.customer_balance_due = invoice_residual - refund_residual
#
#                     # Get all customer payments (including direct payments)
#                     # FIXED: Include both 'posted' and 'paid' states
#                     payments = self.env['account.payment'].search([
#                         ('partner_id', 'child_of', move.partner_id.commercial_partner_id.id),
#                         ('partner_type', '=', 'customer'),
#                         ('payment_type', '=', 'inbound'),
#                         ('state', 'in', ['posted', 'paid'])
#                     ])
#
#                     total_payments = sum(payments.mapped('amount'))
#                     move.customer_total_paid = total_payments
#
#                 # Vendor bills
#                 elif move.move_type in ['in_invoice', 'in_refund']:
#                     bills = self.env['account.move'].search([
#                         ('partner_id', 'child_of', move.partner_id.commercial_partner_id.id),
#                         ('move_type', 'in', ['in_invoice', 'in_refund']),
#                         ('state', '=', 'posted')
#                     ])
#
#                     # Separate bills and refunds
#                     in_invoices = bills.filtered(lambda bill: bill.move_type == 'in_invoice')
#                     in_refunds = bills.filtered(lambda bill: bill.move_type == 'in_refund')
#
#                     total_billed = sum(in_invoices.mapped('amount_total'))
#                     total_refunded = sum(in_refunds.mapped('amount_total'))
#
#                     # Calculate residual separately for bills and refunds
#                     bill_residual = sum(in_invoices.mapped('amount_residual'))
#                     refund_residual = sum(in_refunds.mapped('amount_residual'))
#
#                     move.vendor_total_billed = total_billed - total_refunded
#                     move.vendor_balance_due = bill_residual - refund_residual
#
#                     # Get all vendor payments (including direct payments)
#                     # FIXED: Include both 'posted' and 'paid' states
#                     payments = self.env['account.payment'].search([
#                         ('partner_id', 'child_of', move.partner_id.commercial_partner_id.id),
#                         ('partner_type', '=', 'supplier'),
#                         ('payment_type', '=', 'outbound'),
#                         ('state', 'in', ['posted', 'paid'])
#                     ])
#
#                     total_payments = sum(payments.mapped('amount'))
#                     move.vendor_total_paid = total_payments
#
#             except Exception as e:
#                 _logger.error(f"ERROR computing partner balance for {move.partner_id.name}: {str(e)}", exc_info=True)
#                 move.customer_total_invoiced = 0.0
#                 move.customer_total_paid = 0.0
#                 move.customer_balance_due = 0.0
#                 move.vendor_total_billed = 0.0
#                 move.vendor_total_paid = 0.0
#                 move.vendor_balance_due = 0.0
#
#     def action_view_customer_invoices(self):
#         """Open all customer invoices"""
#         self.ensure_one()
#
#         if not self.partner_id:
#             raise UserError("No customer selected.")
#
#         return {
#             'name': f'Invoices - {self.partner_id.name}',
#             'type': 'ir.actions.act_window',
#             'res_model': 'account.move',
#             'view_mode': 'list,form',
#             'views': [(False, 'list'), (False, 'form')],
#             'domain': [
#                 ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
#                 ('move_type', 'in', ['out_invoice', 'out_refund']),
#                 ('state', '=', 'posted')
#             ],
#             'context': {'create': False},
#         }
#
#     def action_view_customer_payments(self):
#         """Open customer payments"""
#         self.ensure_one()
#
#         if not self.partner_id:
#             raise UserError("No customer selected.")
#
#         # FIXED: Include both 'posted' and 'paid' states
#         return {
#             'name': f'Payments - {self.partner_id.name}',
#             'type': 'ir.actions.act_window',
#             'res_model': 'account.payment',
#             'view_mode': 'list,form',
#             'views': [(False, 'list'), (False, 'form')],
#             'domain': [
#                 ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
#                 ('partner_type', '=', 'customer'),
#                 ('payment_type', '=', 'inbound'),
#                 ('state', 'in', ['posted', 'paid'])
#             ],
#             'context': {
#                 'create': False,
#                 'default_partner_id': self.partner_id.id,
#                 'default_partner_type': 'customer',
#                 'default_payment_type': 'inbound',
#             },
#         }
#
#     def action_view_vendor_bills(self):
#         """Open all vendor bills"""
#         self.ensure_one()
#
#         if not self.partner_id:
#             raise UserError("No vendor selected.")
#
#         return {
#             'name': f'Bills - {self.partner_id.name}',
#             'type': 'ir.actions.act_window',
#             'res_model': 'account.move',
#             'view_mode': 'list,form',
#             'views': [(False, 'list'), (False, 'form')],
#             'domain': [
#                 ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
#                 ('move_type', 'in', ['in_invoice', 'in_refund']),
#                 ('state', '=', 'posted')
#             ],
#             'context': {'create': False},
#         }
#
#     def action_view_vendor_payments(self):
#         """Open vendor payments"""
#         self.ensure_one()
#
#         if not self.partner_id:
#             raise UserError("No vendor selected.")
#
#         # FIXED: Include both 'posted' and 'paid' states
#         return {
#             'name': f'Payments - {self.partner_id.name}',
#             'type': 'ir.actions.act_window',
#             'res_model': 'account.payment',
#             'view_mode': 'list,form',
#             'views': [(False, 'list'), (False, 'form')],
#             'domain': [
#                 ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
#                 ('partner_type', '=', 'supplier'),
#                 ('payment_type', '=', 'outbound'),
#                 ('state', 'in', ['posted', 'paid'])
#             ],
#             'context': {
#                 'create': False,
#                 'default_partner_id': self.partner_id.id,
#                 'default_partner_type': 'supplier',
#                 'default_payment_type': 'outbound',
#             },
#         }

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    # For Customer Invoices - 4 FIELDS
    customer_total_invoiced = fields.Monetary(
        string='Total Invoiced',
        compute='_compute_partner_balance',
        currency_field='currency_id',
        help='Total of all customer invoices (before credit notes)'
    )

    customer_total_credits = fields.Monetary(
        string='Total Credits',
        compute='_compute_partner_balance',
        currency_field='currency_id',
        help='Total credit notes issued to customer'
    )

    customer_total_paid = fields.Monetary(
        string='Amount Received',
        compute='_compute_partner_balance',
        currency_field='currency_id',
        help='Total amount paid by this customer'
    )

    customer_balance_due = fields.Monetary(
        string='Balance Due',
        compute='_compute_partner_balance',
        currency_field='currency_id',
        help='Net balance (Total Invoiced - Credits - Paid)'
    )

    # For Vendor Bills - 4 FIELDS
    vendor_total_billed = fields.Monetary(
        string='Total Billed',
        compute='_compute_partner_balance',
        currency_field='currency_id',
        help='Total of all vendor bills (before credit notes)'
    )

    vendor_total_credits = fields.Monetary(
        string='Total Credits',
        compute='_compute_partner_balance',
        currency_field='currency_id',
        help='Total credit notes from vendor'
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
        help='Net balance (Total Billed - Credits - Paid)'
    )

    @api.depends('partner_id', 'move_type', 'state')
    def _compute_partner_balance(self):
        """Calculate partner financial summary - 4 FIELDS VERSION"""
        for move in self:
            # Reset all fields first
            move.customer_total_invoiced = 0.0
            move.customer_total_credits = 0.0
            move.customer_total_paid = 0.0
            move.customer_balance_due = 0.0
            move.vendor_total_billed = 0.0
            move.vendor_total_credits = 0.0
            move.vendor_total_paid = 0.0
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

                    # Separate invoices and refunds
                    out_invoices = invoices.filtered(lambda inv: inv.move_type == 'out_invoice')
                    out_refunds = invoices.filtered(lambda inv: inv.move_type == 'out_refund')

                    # GROSS amounts (all invoice documents)
                    total_invoiced = sum(out_invoices.mapped('amount_total'))
                    total_credits = sum(out_refunds.mapped('amount_total'))

                    # Calculate residual amounts for balance
                    invoice_residual = sum(out_invoices.mapped('amount_residual'))
                    refund_residual = sum(out_refunds.mapped('amount_residual'))

                    # Set the 4 fields
                    move.customer_total_invoiced = total_invoiced  # Gross invoiced (5,750)
                    move.customer_total_credits = total_credits    # Credit notes (2,875)
                    move.customer_balance_due = invoice_residual - refund_residual  # Balance

                    # Get all customer payments
                    payments = self.env['account.payment'].search([
                        ('partner_id', 'child_of', move.partner_id.commercial_partner_id.id),
                        ('partner_type', '=', 'customer'),
                        ('payment_type', '=', 'inbound'),
                        ('state', 'in', ['posted', 'paid'])
                    ])

                    total_payments = sum(payments.mapped('amount'))
                    move.customer_total_paid = total_payments  # Payments (10,000)

                # Vendor bills
                elif move.move_type in ['in_invoice', 'in_refund']:
                    bills = self.env['account.move'].search([
                        ('partner_id', 'child_of', move.partner_id.commercial_partner_id.id),
                        ('move_type', 'in', ['in_invoice', 'in_refund']),
                        ('state', '=', 'posted')
                    ])

                    # Separate bills and refunds
                    in_invoices = bills.filtered(lambda bill: bill.move_type == 'in_invoice')
                    in_refunds = bills.filtered(lambda bill: bill.move_type == 'in_refund')

                    # GROSS amounts (all bill documents)
                    total_billed = sum(in_invoices.mapped('amount_total'))
                    total_credits = sum(in_refunds.mapped('amount_total'))

                    # Calculate residual
                    bill_residual = sum(in_invoices.mapped('amount_residual'))
                    refund_residual = sum(in_refunds.mapped('amount_residual'))

                    # Set the 4 fields
                    move.vendor_total_billed = total_billed    # Gross billed
                    move.vendor_total_credits = total_credits  # Credit notes
                    move.vendor_balance_due = bill_residual - refund_residual  # Balance

                    # Get all vendor payments
                    payments = self.env['account.payment'].search([
                        ('partner_id', 'child_of', move.partner_id.commercial_partner_id.id),
                        ('partner_type', '=', 'supplier'),
                        ('payment_type', '=', 'outbound'),
                        ('state', 'in', ['posted', 'paid'])
                    ])

                    total_payments = sum(payments.mapped('amount'))
                    move.vendor_total_paid = total_payments  # Payments

            except Exception as e:
                _logger.error(f"ERROR computing partner balance for {move.partner_id.name}: {str(e)}", exc_info=True)
                move.customer_total_invoiced = 0.0
                move.customer_total_credits = 0.0
                move.customer_total_paid = 0.0
                move.customer_balance_due = 0.0
                move.vendor_total_billed = 0.0
                move.vendor_total_credits = 0.0
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

    def action_view_customer_credits(self):
        """Open all customer credit notes"""
        self.ensure_one()

        if not self.partner_id:
            raise UserError("No customer selected.")

        return {
            'name': f'Credit Notes - {self.partner_id.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],
            'domain': [
                ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
                ('move_type', '=', 'out_refund'),
                ('state', '=', 'posted')
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
        """Open all vendor credit notes"""
        self.ensure_one()

        if not self.partner_id:
            raise UserError("No vendor selected.")

        return {
            'name': f'Credit Notes - {self.partner_id.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],
            'domain': [
                ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
                ('move_type', '=', 'in_refund'),
                ('state', '=', 'posted')
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
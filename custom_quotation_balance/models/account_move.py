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
#                     _logger.info(
#                         f"DEBUG Customer {move.partner_id.name}: Found {len(invoices)} posted invoices/credit notes")
#
#                     # Separate invoices and refunds
#                     out_invoices = invoices.filtered(lambda inv: inv.move_type == 'out_invoice')
#                     out_refunds = invoices.filtered(lambda inv: inv.move_type == 'out_refund')
#
#                     _logger.info(f"DEBUG: {len(out_invoices)} invoices, {len(out_refunds)} credit notes")
#
#                     total_invoiced = sum(out_invoices.mapped('amount_total'))
#                     total_refunded = sum(out_refunds.mapped('amount_total'))
#
#                     # Calculate residual separately for invoices and refunds
#                     invoice_residual = sum(out_invoices.mapped('amount_residual'))
#                     refund_residual = sum(out_refunds.mapped('amount_residual'))
#
#                     _logger.info(
#                         f"DEBUG: Invoiced={total_invoiced}, Refunded={total_refunded}, InvResidual={invoice_residual}, RefResidual={refund_residual}")
#
#                     move.customer_total_invoiced = total_invoiced - total_refunded
#                     move.customer_balance_due = invoice_residual - refund_residual
#                     move.customer_total_paid = move.customer_total_invoiced - move.customer_balance_due
#
#                     _logger.info(
#                         f"DEBUG FINAL: TotalInvoiced={move.customer_total_invoiced}, Paid={move.customer_total_paid}, Due={move.customer_balance_due}")
#
#                 # Vendor bills
#                 elif move.move_type in ['in_invoice', 'in_refund']:
#                     bills = self.env['account.move'].search([
#                         ('partner_id', 'child_of', move.partner_id.commercial_partner_id.id),
#                         ('move_type', 'in', ['in_invoice', 'in_refund']),
#                         ('state', '=', 'posted')
#                     ])
#
#                     _logger.info(f"DEBUG Vendor {move.partner_id.name}: Found {len(bills)} posted bills/refunds")
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
#                     move.vendor_total_paid = move.vendor_total_billed - move.vendor_balance_due
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
#         all_payments = self.env['account.payment'].search([
#             ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
#         ])
#
#         if not all_payments:
#             return {
#                 'name': f'Paid Invoices - {self.partner_id.name}',
#                 'type': 'ir.actions.act_window',
#                 'res_model': 'account.move',
#                 'view_mode': 'list,form',
#                 'views': [(False, 'list'), (False, 'form')],
#                 'domain': [
#                     ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
#                     ('payment_state', 'in', ['paid', 'in_payment', 'partial']),
#                     ('state', '=', 'posted'),
#                 ],
#                 'context': {'create': False},
#             }
#
#         return {
#             'name': f'Payments - {self.partner_id.name}',
#             'type': 'ir.actions.act_window',
#             'res_model': 'account.payment',
#             'view_mode': 'list,form',
#             'views': [(False, 'list'), (False, 'form')],
#             'domain': [
#                 ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
#                 ('payment_type', '=', 'inbound'),
#             ],
#             'context': {
#                 'create': False,
#                 'default_partner_id': self.partner_id.id,
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
#         all_payments = self.env['account.payment'].search([
#             ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
#         ])
#
#         if not all_payments:
#             return {
#                 'name': f'Paid Bills - {self.partner_id.name}',
#                 'type': 'ir.actions.act_window',
#                 'res_model': 'account.move',
#                 'view_mode': 'list,form',
#                 'views': [(False, 'list'), (False, 'form')],
#                 'domain': [
#                     ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
#                     ('payment_state', 'in', ['paid', 'in_payment', 'partial']),
#                     ('state', '=', 'posted'),
#                 ],
#                 'context': {'create': False},
#             }
#
#         return {
#             'name': f'Payments - {self.partner_id.name}',
#             'type': 'ir.actions.act_window',
#             'res_model': 'account.payment',
#             'view_mode': 'list,form',
#             'views': [(False, 'list'), (False, 'form')],
#             'domain': [
#                 ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
#                 ('payment_type', '=', 'outbound'),
#             ],
#             'context': {
#                 'create': False,
#                 'default_partner_id': self.partner_id.id,
#                 'default_payment_type': 'outbound',
#             },
#         }

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


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

    @api.depends('partner_id', 'move_type', 'state')
    def _compute_partner_balance(self):
        """Calculate partner financial summary based on invoice type"""
        for move in self:
            # Reset all fields first
            move.customer_total_invoiced = 0.0
            move.customer_total_paid = 0.0
            move.customer_balance_due = 0.0
            move.vendor_total_billed = 0.0
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

                    total_invoiced = sum(out_invoices.mapped('amount_total'))
                    total_refunded = sum(out_refunds.mapped('amount_total'))

                    # Calculate residual separately for invoices and refunds
                    invoice_residual = sum(out_invoices.mapped('amount_residual'))
                    refund_residual = sum(out_refunds.mapped('amount_residual'))

                    move.customer_total_invoiced = total_invoiced - total_refunded
                    move.customer_balance_due = invoice_residual - refund_residual

                    # Get all customer payments (including direct payments)
                    # Changed: Only use 'posted' state to get confirmed payments
                    payments = self.env['account.payment'].search([
                        ('partner_id', 'child_of', move.partner_id.commercial_partner_id.id),
                        ('partner_type', '=', 'customer'),
                        ('payment_type', '=', 'inbound'),
                        ('state', '=', 'posted')
                    ])

                    total_payments = sum(payments.mapped('amount'))
                    move.customer_total_paid = total_payments

                    _logger.info(
                        f"Customer {move.partner_id.name}: Invoiced={move.customer_total_invoiced}, "
                        f"Payments={move.customer_total_paid}, Due={move.customer_balance_due}"
                    )

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

                    total_billed = sum(in_invoices.mapped('amount_total'))
                    total_refunded = sum(in_refunds.mapped('amount_total'))

                    # Calculate residual separately for bills and refunds
                    bill_residual = sum(in_invoices.mapped('amount_residual'))
                    refund_residual = sum(in_refunds.mapped('amount_residual'))

                    move.vendor_total_billed = total_billed - total_refunded
                    move.vendor_balance_due = bill_residual - refund_residual

                    # Get all vendor payments (including direct payments)
                    # Changed: Only use 'posted' state and add partner_type
                    payments = self.env['account.payment'].search([
                        ('partner_id', 'child_of', move.partner_id.commercial_partner_id.id),
                        ('partner_type', '=', 'supplier'),
                        ('payment_type', '=', 'outbound'),
                        ('state', '=', 'posted')
                    ])

                    total_payments = sum(payments.mapped('amount'))
                    move.vendor_total_paid = total_payments

            except Exception as e:
                _logger.error(f"ERROR computing partner balance for {move.partner_id.name}: {str(e)}", exc_info=True)
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
                ('state', '=', 'posted')
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
                ('state', '=', 'posted')
            ],
            'context': {
                'create': False,
                'default_partner_id': self.partner_id.id,
                'default_partner_type': 'supplier',
                'default_payment_type': 'outbound',
            },
        }
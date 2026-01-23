# from odoo import models, fields, api
# from odoo.exceptions import UserError
#
#
# class PurchaseOrder(models.Model):
#     _inherit = 'purchase.order'
#
#     vendor_total_billed = fields.Monetary(
#         string='Total Billed',
#         compute='_compute_vendor_balance',
#         currency_field='currency_id',
#         help='Click to view all vendor bills'
#     )
#
#     vendor_total_paid = fields.Monetary(
#         string='Amount Paid',
#         compute='_compute_vendor_balance',
#         currency_field='currency_id',
#         help='Click to view all vendor payments'
#     )
#
#     vendor_balance_due = fields.Monetary(
#         string='Balance Due',
#         compute='_compute_vendor_balance',
#         currency_field='currency_id',
#         help='Remaining balance (Total Billed - Amount Paid)'
#     )
#
#     @api.depends('partner_id')
#     def _compute_vendor_balance(self):
#         """Calculate vendor financial summary"""
#         for order in self:
#             if order.partner_id:
#                 try:
#                     if 'account.move' not in self.env:
#                         order.vendor_total_billed = 0.0
#                         order.vendor_total_paid = 0.0
#                         order.vendor_balance_due = 0.0
#                         continue
#
#                     bills = self.env['account.move'].search([
#                         ('partner_id', 'child_of', order.partner_id.commercial_partner_id.id),
#                         ('move_type', 'in', ['in_invoice', 'in_refund']),
#                         ('state', '=', 'posted')
#                     ])
#
#                     total_billed = sum(bills.filtered(
#                         lambda bill: bill.move_type == 'in_invoice'
#                     ).mapped('amount_total'))
#
#                     total_refunded = sum(bills.filtered(
#                         lambda bill: bill.move_type == 'in_refund'
#                     ).mapped('amount_total'))
#
#                     total_residual = sum(bills.mapped('amount_residual'))
#
#                     order.vendor_total_billed = total_billed - total_refunded
#                     order.vendor_balance_due = total_residual
#                     order.vendor_total_paid = order.vendor_total_billed - order.vendor_balance_due
#                 except Exception as e:
#                     order.vendor_total_billed = 0.0
#                     order.vendor_total_paid = 0.0
#                     order.vendor_balance_due = 0.0
#             else:
#                 order.vendor_total_billed = 0.0
#                 order.vendor_total_paid = 0.0
#                 order.vendor_balance_due = 0.0
#
#     def action_view_vendor_bills(self):
#         """Open filtered list of vendor bills"""
#         self.ensure_one()
#
#         if not self.partner_id:
#             raise UserError("Please select a vendor first.")
#
#         domain = [
#             ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
#             ('move_type', 'in', ['in_invoice', 'in_refund']),
#             ('state', '=', 'posted')
#         ]
#
#         return {
#             'name': f'Bills - {self.partner_id.name}',
#             'type': 'ir.actions.act_window',
#             'res_model': 'account.move',
#             'view_mode': 'list,form',
#             'views': [(False, 'list'), (False, 'form')],
#             'domain': domain,
#             'context': {
#                 'create': False,
#                 'default_move_type': 'in_invoice',
#             },
#         }
#
#     def action_view_vendor_payments(self):
#         """Open filtered list of vendor payments"""
#         self.ensure_one()
#
#         if not self.partner_id:
#             raise UserError("Please select a vendor first.")
#
#         # Check if account.payment model exists
#         if 'account.payment' not in self.env:
#             raise UserError("Payment module is not installed.")
#
#         # Search for all payments for this vendor (no filters)
#         all_payments = self.env['account.payment'].search([
#             ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
#         ])
#
#         # Debug: Show what we found
#         if not all_payments:
#             # No account.payment records - try account.move with payment_state
#             moves_with_payment = self.env['account.move'].search([
#                 ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
#                 ('payment_state', 'in', ['paid', 'in_payment', 'partial']),
#                 ('state', '=', 'posted'),
#             ])
#
#             if moves_with_payment:
#                 return {
#                     'name': f'Paid Bills - {self.partner_id.name}',
#                     'type': 'ir.actions.act_window',
#                     'res_model': 'account.move',
#                     'view_mode': 'list,form',
#                     'views': [(False, 'list'), (False, 'form')],
#                     'domain': [
#                         ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
#                         ('payment_state', 'in', ['paid', 'in_payment', 'partial']),
#                         ('state', '=', 'posted'),
#                     ],
#                     'context': {'create': False},
#                 }
#             else:
#                 raise UserError(
#                     f"No payment records found for {self.partner_id.name}.\n\nThis could mean:\n1. No payments have been recorded yet\n2. Payments are recorded in a different way in your Odoo Mates installation\n3. The accounting module uses a custom payment model")
#
#         # We found account.payment records - now show them
#         domain = [
#             ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
#             ('payment_type', '=', 'outbound'),
#         ]
#
#         return {
#             'name': f'Payments - {self.partner_id.name}',
#             'type': 'ir.actions.act_window',
#             'res_model': 'account.payment',
#             'view_mode': 'list,form',
#             'views': [(False, 'list'), (False, 'form')],
#             'domain': domain,
#             'context': {
#                 'create': False,
#                 'default_partner_id': self.partner_id.id,
#                 'default_payment_type': 'outbound',
#             },
#         }

from odoo import models, fields, api
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    vendor_total_billed = fields.Monetary(
        string='Total Billed',
        compute='_compute_vendor_balance',
        currency_field='currency_id',
        help='Click to view all vendor bills'
    )

    vendor_total_paid = fields.Monetary(
        string='Amount Paid',
        compute='_compute_vendor_balance',
        currency_field='currency_id',
        help='Click to view all vendor payments'
    )

    vendor_balance_due = fields.Monetary(
        string='Balance Due',
        compute='_compute_vendor_balance',
        currency_field='currency_id',
        help='Remaining balance (Total Billed - Amount Paid)'
    )

    @api.depends('partner_id')
    def _compute_vendor_balance(self):
        """Calculate vendor financial summary"""
        for order in self:
            if order.partner_id:
                try:
                    if 'account.move' not in self.env:
                        order.vendor_total_billed = 0.0
                        order.vendor_total_paid = 0.0
                        order.vendor_balance_due = 0.0
                        continue

                    bills = self.env['account.move'].search([
                        ('partner_id', 'child_of', order.partner_id.commercial_partner_id.id),
                        ('move_type', 'in', ['in_invoice', 'in_refund']),
                        ('state', '=', 'posted')
                    ])

                    total_billed = sum(bills.filtered(
                        lambda bill: bill.move_type == 'in_invoice'
                    ).mapped('amount_total'))

                    total_refunded = sum(bills.filtered(
                        lambda bill: bill.move_type == 'in_refund'
                    ).mapped('amount_total'))

                    total_residual = sum(bills.mapped('amount_residual'))

                    order.vendor_total_billed = total_billed - total_refunded
                    order.vendor_balance_due = total_residual

                    # Get all vendor payments (including direct payments)
                    payments = self.env['account.payment'].search([
                        ('partner_id', 'child_of', order.partner_id.commercial_partner_id.id),
                        ('partner_type', '=', 'supplier'),
                        ('payment_type', '=', 'outbound'),
                        ('state', '=', 'posted')
                    ])

                    total_payments = sum(payments.mapped('amount'))
                    order.vendor_total_paid = total_payments

                except Exception as e:
                    order.vendor_total_billed = 0.0
                    order.vendor_total_paid = 0.0
                    order.vendor_balance_due = 0.0
            else:
                order.vendor_total_billed = 0.0
                order.vendor_total_paid = 0.0
                order.vendor_balance_due = 0.0

    def action_view_vendor_bills(self):
        """Open filtered list of vendor bills"""
        self.ensure_one()

        if not self.partner_id:
            raise UserError("Please select a vendor first.")

        domain = [
            ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
            ('move_type', 'in', ['in_invoice', 'in_refund']),
            ('state', '=', 'posted')
        ]

        return {
            'name': f'Bills - {self.partner_id.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],
            'domain': domain,
            'context': {
                'create': False,
                'default_move_type': 'in_invoice',
            },
        }

    def action_view_vendor_payments(self):
        """Open filtered list of vendor payments"""
        self.ensure_one()

        if not self.partner_id:
            raise UserError("Please select a vendor first.")

        if 'account.payment' not in self.env:
            raise UserError("Payment module is not installed.")

        domain = [
            ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
            ('partner_type', '=', 'supplier'),
            ('payment_type', '=', 'outbound'),
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
                'default_partner_type': 'supplier',
                'default_payment_type': 'outbound',
            },
        }
# # from odoo import models, fields, api
# # from odoo.exceptions import UserError
# #
# #
# # class SaleOrder(models.Model):
# #     _inherit = 'sale.order'
# #
# #     customer_total_invoiced = fields.Monetary(
# #         string='Total Invoiced',
# #         compute='_compute_customer_balance',
# #         currency_field='currency_id',
# #         help='Click to view all customer invoices'
# #     )
# #
# #     customer_total_paid = fields.Monetary(
# #         string='Amount Paid',
# #         compute='_compute_customer_balance',
# #         currency_field='currency_id',
# #         help='Click to view all customer payments'
# #     )
# #
# #     customer_balance_due = fields.Monetary(
# #         string='Balance Due',
# #         compute='_compute_customer_balance',
# #         currency_field='currency_id',
# #         help='Remaining balance (Total Invoiced - Amount Paid)'
# #     )
# #
# #     @api.depends('partner_id')
# #     def _compute_customer_balance(self):
# #         """Calculate customer financial summary"""
# #         for order in self:
# #             if order.partner_id:
# #                 try:
# #                     if 'account.move' not in self.env:
# #                         order.customer_total_invoiced = 0.0
# #                         order.customer_total_paid = 0.0
# #                         order.customer_balance_due = 0.0
# #                         continue
# #
# #                     invoices = self.env['account.move'].search([
# #                         ('partner_id', 'child_of', order.partner_id.commercial_partner_id.id),
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
# #                     order.customer_total_invoiced = total_invoiced - total_refunded
# #                     order.customer_balance_due = total_residual
# #
# #                     # Get all customer payments (including direct payments)
# #                     # FIXED: Include both 'posted' and 'paid' states
# #                     payments = self.env['account.payment'].search([
# #                         ('partner_id', 'child_of', order.partner_id.commercial_partner_id.id),
# #                         ('partner_type', '=', 'customer'),
# #                         ('payment_type', '=', 'inbound'),
# #                         ('state', 'in', ['posted', 'paid'])
# #                     ])
# #
# #                     total_payments = sum(payments.mapped('amount'))
# #                     order.customer_total_paid = total_payments
# #
# #                 except Exception as e:
# #                     order.customer_total_invoiced = 0.0
# #                     order.customer_total_paid = 0.0
# #                     order.customer_balance_due = 0.0
# #             else:
# #                 order.customer_total_invoiced = 0.0
# #                 order.customer_total_paid = 0.0
# #                 order.customer_balance_due = 0.0
# #
# #     def action_view_customer_invoices(self):
# #         """Open filtered list of customer invoices"""
# #         self.ensure_one()
# #
# #         if not self.partner_id:
# #             raise UserError("Please select a customer first.")
# #
# #         domain = [
# #             ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
# #             ('move_type', 'in', ['out_invoice', 'out_refund']),
# #             ('state', '=', 'posted')
# #         ]
# #
# #         return {
# #             'name': f'Invoices - {self.partner_id.name}',
# #             'type': 'ir.actions.act_window',
# #             'res_model': 'account.move',
# #             'view_mode': 'list,form',
# #             'views': [(False, 'list'), (False, 'form')],
# #             'domain': domain,
# #             'context': {
# #                 'create': False,
# #                 'default_move_type': 'out_invoice',
# #             },
# #         }
# #
# #     def action_view_customer_payments(self):
# #         """Open filtered list of customer payments"""
# #         self.ensure_one()
# #
# #         if not self.partner_id:
# #             raise UserError("Please select a customer first.")
# #
# #         if 'account.payment' not in self.env:
# #             raise UserError("Payment module is not installed.")
# #
# #         # FIXED: Include both 'posted' and 'paid' states
# #         domain = [
# #             ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
# #             ('partner_type', '=', 'customer'),
# #             ('payment_type', '=', 'inbound'),
# #             ('state', 'in', ['posted', 'paid'])
# #         ]
# #
# #         return {
# #             'name': f'Payments - {self.partner_id.name}',
# #             'type': 'ir.actions.act_window',
# #             'res_model': 'account.payment',
# #             'view_mode': 'list,form',
# #             'views': [(False, 'list'), (False, 'form')],
# #             'domain': domain,
# #             'context': {
# #                 'create': False,
# #                 'default_partner_id': self.partner_id.id,
# #                 'default_partner_type': 'customer',
# #                 'default_payment_type': 'inbound',
# #             },
# #         }
#
# from odoo import models, fields, api
# from odoo.exceptions import UserError
#
#
# class SaleOrder(models.Model):
#     _inherit = 'sale.order'
#
#     # Customer Balance - 4 FIELDS
#     customer_total_invoiced = fields.Monetary(
#         string='Total Invoiced',
#         compute='_compute_customer_balance',
#         currency_field='currency_id',
#         help='Total of all customer invoices (before credit notes)'
#     )
#
#     customer_total_credits = fields.Monetary(
#         string='Total Credits',
#         compute='_compute_customer_balance',
#         currency_field='currency_id',
#         help='Total credit notes issued to customer'
#     )
#
#     customer_total_paid = fields.Monetary(
#         string='Amount Paid',
#         compute='_compute_customer_balance',
#         currency_field='currency_id',
#         help='Total amount paid by customer'
#     )
#
#     customer_balance_due = fields.Monetary(
#         string='Balance Due',
#         compute='_compute_customer_balance',
#         currency_field='currency_id',
#         help='Net balance: (Invoiced - Credits - Paid)'
#     )
#
#     @api.depends('partner_id')
#     def _compute_customer_balance(self):
#         """
#         Calculate customer financial summary - SIMPLE METHOD
#         For Sales Orders, show complete financial picture
#         """
#         for order in self:
#             if order.partner_id:
#                 try:
#                     if 'account.move' not in self.env:
#                         order.customer_total_invoiced = 0.0
#                         order.customer_total_credits = 0.0
#                         order.customer_total_paid = 0.0
#                         order.customer_balance_due = 0.0
#                         continue
#
#                     invoices = self.env['account.move'].search([
#                         ('partner_id', 'child_of', order.partner_id.commercial_partner_id.id),
#                         ('move_type', 'in', ['out_invoice', 'out_refund']),
#                         ('state', '=', 'posted')
#                     ])
#
#                     # Separate invoices and credit notes
#                     out_invoices = invoices.filtered(lambda inv: inv.move_type == 'out_invoice')
#                     out_refunds = invoices.filtered(lambda inv: inv.move_type == 'out_refund')
#
#                     # Calculate totals
#                     total_invoiced = sum(out_invoices.mapped('amount_total'))
#                     total_credits = sum(out_refunds.mapped('amount_total'))
#
#                     order.customer_total_invoiced = total_invoiced
#                     order.customer_total_credits = total_credits
#
#                     # Get all customer payments
#                     payments = self.env['account.payment'].search([
#                         ('partner_id', 'child_of', order.partner_id.commercial_partner_id.id),
#                         ('partner_type', '=', 'customer'),
#                         ('payment_type', '=', 'inbound'),
#                         ('state', 'in', ['posted', 'paid'])
#                     ])
#
#                     total_payments = sum(payments.mapped('amount'))
#                     order.customer_total_paid = total_payments
#
#                     # SIMPLE CALCULATION for Sales Orders
#                     # Shows complete financial picture
#                     order.customer_balance_due = (total_invoiced - total_credits) - total_payments
#
#                 except Exception as e:
#                     order.customer_total_invoiced = 0.0
#                     order.customer_total_credits = 0.0
#                     order.customer_total_paid = 0.0
#                     order.customer_balance_due = 0.0
#             else:
#                 order.customer_total_invoiced = 0.0
#                 order.customer_total_credits = 0.0
#                 order.customer_total_paid = 0.0
#                 order.customer_balance_due = 0.0
#
#     def action_view_customer_invoices(self):
#         """Open filtered list of customer invoices"""
#         self.ensure_one()
#
#         if not self.partner_id:
#             raise UserError("Please select a customer first.")
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
#     def action_view_customer_credits(self):
#         """Open customer credit notes"""
#         self.ensure_one()
#
#         if not self.partner_id:
#             raise UserError("Please select a customer first.")
#
#         return {
#             'name': f'Credit Notes - {self.partner_id.name}',
#             'type': 'ir.actions.act_window',
#             'res_model': 'account.move',
#             'view_mode': 'list,form',
#             'views': [(False, 'list'), (False, 'form')],
#             'domain': [
#                 ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
#                 ('move_type', '=', 'out_refund'),
#                 ('state', '=', 'posted')
#             ],
#             'context': {'create': False},
#         }
#
#     def action_view_customer_payments(self):
#         """Open filtered list of customer payments"""
#         self.ensure_one()
#
#         if not self.partner_id:
#             raise UserError("Please select a customer first.")
#
#         if 'account.payment' not in self.env:
#             raise UserError("Payment module is not installed.")
#
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


from odoo import models, fields, api
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    customer_total_invoiced = fields.Monetary(
        string='Total Invoiced',
        compute='_compute_customer_balance',
        currency_field='currency_id',
        help='Total of all customer invoices'
    )

    customer_total_received = fields.Monetary(
        string='Amount Received',
        compute='_compute_customer_balance',
        currency_field='currency_id',
        help='Total payments + credit notes'
    )

    customer_balance_due = fields.Monetary(
        string='Balance Due',
        compute='_compute_customer_balance',
        currency_field='currency_id',
        help='Net balance: (Invoiced - Received)'
    )

    @api.depends('partner_id')
    def _compute_customer_balance(self):
        for order in self:
            if order.partner_id:
                try:
                    if 'account.move' not in self.env:
                        order.customer_total_invoiced = 0.0
                        order.customer_total_received = 0.0
                        order.customer_balance_due = 0.0
                        continue

                    invoices = self.env['account.move'].search([
                        ('partner_id', 'child_of', order.partner_id.commercial_partner_id.id),
                        ('move_type', 'in', ['out_invoice', 'out_refund']),
                        ('state', '=', 'posted')
                    ])

                    out_invoices = invoices.filtered(lambda inv: inv.move_type == 'out_invoice')
                    out_refunds = invoices.filtered(lambda inv: inv.move_type == 'out_refund')

                    total_invoiced = sum(out_invoices.mapped('amount_total'))
                    total_credits = sum(out_refunds.mapped('amount_total'))

                    order.customer_total_invoiced = total_invoiced

                    payments = self.env['account.payment'].search([
                        ('partner_id', 'child_of', order.partner_id.commercial_partner_id.id),
                        ('partner_type', '=', 'customer'),
                        ('payment_type', '=', 'inbound'),
                        ('state', 'in', ['posted', 'paid'])
                    ])

                    total_payments = sum(payments.mapped('amount'))

                    order.customer_total_received = total_payments + total_credits
                    order.customer_balance_due = total_invoiced - (total_payments + total_credits)

                except Exception as e:
                    order.customer_total_invoiced = 0.0
                    order.customer_total_received = 0.0
                    order.customer_balance_due = 0.0
            else:
                order.customer_total_invoiced = 0.0
                order.customer_total_received = 0.0
                order.customer_balance_due = 0.0

    def action_view_customer_invoices(self):
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

    def action_view_customer_payments(self):
        self.ensure_one()
        if not self.partner_id:
            raise UserError("Please select a customer first.")

        if 'account.payment' not in self.env:
            raise UserError("Payment module is not installed.")

        return {
            'name': f'Payments & Credits - {self.partner_id.name}',
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
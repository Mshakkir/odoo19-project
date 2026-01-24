# from odoo import models, fields, api
# from odoo.exceptions import UserError
#
#
# class StockPicking(models.Model):
#     _inherit = 'stock.picking'
#
#     partner_total_invoiced = fields.Monetary(
#         string='Total Invoiced/Billed',
#         compute='_compute_partner_balance',
#         currency_field='currency_id',
#         help='Total invoiced or billed for this partner',
#         store=False
#     )
#
#     partner_total_paid = fields.Monetary(
#         string='Amount Paid',
#         compute='_compute_partner_balance',
#         currency_field='currency_id',
#         help='Total amount paid',
#         store=False
#     )
#
#     partner_balance_due = fields.Monetary(
#         string='Balance Due',
#         compute='_compute_partner_balance',
#         currency_field='currency_id',
#         help='Remaining balance',
#         store=False
#     )
#
#     currency_id = fields.Many2one(
#         'res.currency',
#         string='Currency',
#         compute='_compute_currency',
#         store=False
#     )
#
#     @api.depends('company_id')
#     def _compute_currency(self):
#         """Get company currency"""
#         for picking in self:
#             picking.currency_id = picking.company_id.currency_id or self.env.company.currency_id
#
#     @api.depends('partner_id', 'picking_type_id', 'picking_type_id.code')
#     def _compute_partner_balance(self):
#         """Calculate partner financial summary based on picking type"""
#         for picking in self:
#             # Reset values
#             picking.partner_total_invoiced = 0.0
#             picking.partner_total_paid = 0.0
#             picking.partner_balance_due = 0.0
#
#             # Need at least a partner
#             if not picking.partner_id:
#                 continue
#
#             try:
#                 # If picking_type_id is set, use it to determine customer/vendor
#                 if picking.picking_type_id and picking.picking_type_id.code:
#
#                     # Delivery orders (customer)
#                     if picking.picking_type_id.code == 'outgoing':
#                         invoices = self.env['account.move'].search([
#                             ('partner_id', 'child_of', picking.partner_id.commercial_partner_id.id),
#                             ('move_type', 'in', ['out_invoice', 'out_refund']),
#                             ('state', '=', 'posted')
#                         ])
#
#                         out_invoices = invoices.filtered(lambda inv: inv.move_type == 'out_invoice')
#                         out_refunds = invoices.filtered(lambda inv: inv.move_type == 'out_refund')
#
#                         total_invoiced = sum(out_invoices.mapped('amount_total'))
#                         total_refunded = sum(out_refunds.mapped('amount_total'))
#
#                         invoice_residual = sum(out_invoices.mapped('amount_residual'))
#                         refund_residual = sum(out_refunds.mapped('amount_residual'))
#
#                         picking.partner_total_invoiced = total_invoiced - total_refunded
#                         picking.partner_balance_due = invoice_residual - refund_residual
#
#                         # Get all customer payments (including direct payments)
#                         # FIXED: Include both 'posted' and 'paid' states
#                         payments = self.env['account.payment'].search([
#                             ('partner_id', 'child_of', picking.partner_id.commercial_partner_id.id),
#                             ('partner_type', '=', 'customer'),
#                             ('payment_type', '=', 'inbound'),
#                             ('state', 'in', ['posted', 'paid'])
#                         ])
#                         picking.partner_total_paid = sum(payments.mapped('amount'))
#
#                     # Receipts (vendor)
#                     elif picking.picking_type_id.code == 'incoming':
#                         bills = self.env['account.move'].search([
#                             ('partner_id', 'child_of', picking.partner_id.commercial_partner_id.id),
#                             ('move_type', 'in', ['in_invoice', 'in_refund']),
#                             ('state', '=', 'posted')
#                         ])
#
#                         in_invoices = bills.filtered(lambda bill: bill.move_type == 'in_invoice')
#                         in_refunds = bills.filtered(lambda bill: bill.move_type == 'in_refund')
#
#                         total_billed = sum(in_invoices.mapped('amount_total'))
#                         total_refunded = sum(in_refunds.mapped('amount_total'))
#
#                         bill_residual = sum(in_invoices.mapped('amount_residual'))
#                         refund_residual = sum(in_refunds.mapped('amount_residual'))
#
#                         picking.partner_total_invoiced = total_billed - total_refunded
#                         picking.partner_balance_due = bill_residual - refund_residual
#
#                         # Get all vendor payments (including direct payments)
#                         # FIXED: Include both 'posted' and 'paid' states
#                         payments = self.env['account.payment'].search([
#                             ('partner_id', 'child_of', picking.partner_id.commercial_partner_id.id),
#                             ('partner_type', '=', 'supplier'),
#                             ('payment_type', '=', 'outbound'),
#                             ('state', 'in', ['posted', 'paid'])
#                         ])
#                         picking.partner_total_paid = sum(payments.mapped('amount'))
#
#                 else:
#                     # No picking_type_id set yet - determine from location
#                     if picking.location_dest_id and picking.location_dest_id.usage == 'customer':
#                         # Delivery - show customer balance
#                         invoices = self.env['account.move'].search([
#                             ('partner_id', 'child_of', picking.partner_id.commercial_partner_id.id),
#                             ('move_type', 'in', ['out_invoice', 'out_refund']),
#                             ('state', '=', 'posted')
#                         ])
#
#                         out_invoices = invoices.filtered(lambda inv: inv.move_type == 'out_invoice')
#                         out_refunds = invoices.filtered(lambda inv: inv.move_type == 'out_refund')
#
#                         total_invoiced = sum(out_invoices.mapped('amount_total'))
#                         total_refunded = sum(out_refunds.mapped('amount_total'))
#
#                         invoice_residual = sum(out_invoices.mapped('amount_residual'))
#                         refund_residual = sum(out_refunds.mapped('amount_residual'))
#
#                         picking.partner_total_invoiced = total_invoiced - total_refunded
#                         picking.partner_balance_due = invoice_residual - refund_residual
#
#                         # Get all customer payments (including direct payments)
#                         # FIXED: Include both 'posted' and 'paid' states
#                         payments = self.env['account.payment'].search([
#                             ('partner_id', 'child_of', picking.partner_id.commercial_partner_id.id),
#                             ('partner_type', '=', 'customer'),
#                             ('payment_type', '=', 'inbound'),
#                             ('state', 'in', ['posted', 'paid'])
#                         ])
#                         picking.partner_total_paid = sum(payments.mapped('amount'))
#
#                     elif picking.location_id and picking.location_id.usage == 'supplier':
#                         # Receipt - show vendor balance
#                         bills = self.env['account.move'].search([
#                             ('partner_id', 'child_of', picking.partner_id.commercial_partner_id.id),
#                             ('move_type', 'in', ['in_invoice', 'in_refund']),
#                             ('state', '=', 'posted')
#                         ])
#
#                         in_invoices = bills.filtered(lambda bill: bill.move_type == 'in_invoice')
#                         in_refunds = bills.filtered(lambda bill: bill.move_type == 'in_refund')
#
#                         total_billed = sum(in_invoices.mapped('amount_total'))
#                         total_refunded = sum(in_refunds.mapped('amount_total'))
#
#                         bill_residual = sum(in_invoices.mapped('amount_residual'))
#                         refund_residual = sum(in_refunds.mapped('amount_residual'))
#
#                         picking.partner_total_invoiced = total_billed - total_refunded
#                         picking.partner_balance_due = bill_residual - refund_residual
#
#                         # Get all vendor payments (including direct payments)
#                         # FIXED: Include both 'posted' and 'paid' states
#                         payments = self.env['account.payment'].search([
#                             ('partner_id', 'child_of', picking.partner_id.commercial_partner_id.id),
#                             ('partner_type', '=', 'supplier'),
#                             ('payment_type', '=', 'outbound'),
#                             ('state', 'in', ['posted', 'paid'])
#                         ])
#                         picking.partner_total_paid = sum(payments.mapped('amount'))
#
#                     else:
#                         # Default to customer data
#                         invoices = self.env['account.move'].search([
#                             ('partner_id', 'child_of', picking.partner_id.commercial_partner_id.id),
#                             ('move_type', 'in', ['out_invoice', 'out_refund']),
#                             ('state', '=', 'posted')
#                         ])
#
#                         out_invoices = invoices.filtered(lambda inv: inv.move_type == 'out_invoice')
#                         out_refunds = invoices.filtered(lambda inv: inv.move_type == 'out_refund')
#
#                         total_invoiced = sum(out_invoices.mapped('amount_total'))
#                         total_refunded = sum(out_refunds.mapped('amount_total'))
#
#                         invoice_residual = sum(out_invoices.mapped('amount_residual'))
#                         refund_residual = sum(out_refunds.mapped('amount_residual'))
#
#                         picking.partner_total_invoiced = total_invoiced - total_refunded
#                         picking.partner_balance_due = invoice_residual - refund_residual
#
#                         # Get all customer payments (including direct payments)
#                         # FIXED: Include both 'posted' and 'paid' states
#                         payments = self.env['account.payment'].search([
#                             ('partner_id', 'child_of', picking.partner_id.commercial_partner_id.id),
#                             ('partner_type', '=', 'customer'),
#                             ('payment_type', '=', 'inbound'),
#                             ('state', 'in', ['posted', 'paid'])
#                         ])
#                         picking.partner_total_paid = sum(payments.mapped('amount'))
#
#             except Exception:
#                 picking.partner_total_invoiced = 0.0
#                 picking.partner_total_paid = 0.0
#                 picking.partner_balance_due = 0.0
#
#     def action_view_partner_invoices(self):
#         """Open partner invoices/bills based on picking type"""
#         self.ensure_one()
#
#         if not self.partner_id:
#             raise UserError("No partner selected.")
#
#         if self.picking_type_id and self.picking_type_id.code == 'outgoing':
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
#             # Vendor bills (or default)
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
#         """Open partner payments based on picking type"""
#         self.ensure_one()
#
#         if not self.partner_id:
#             raise UserError("No partner selected.")
#
#         # Determine partner type and payment type
#         if self.picking_type_id and self.picking_type_id.code == 'outgoing':
#             partner_type = 'customer'
#             payment_type = 'inbound'
#         else:
#             partner_type = 'supplier'
#             payment_type = 'outbound'
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
#                 ('partner_type', '=', partner_type),
#                 ('payment_type', '=', payment_type),
#                 ('state', 'in', ['posted', 'paid'])
#             ],
#             'context': {
#                 'create': False,
#                 'default_partner_id': self.partner_id.id,
#                 'default_partner_type': partner_type,
#                 'default_payment_type': payment_type,
#             },
#         }

from odoo import models, fields, api
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # Partner Balance - 4 FIELDS
    partner_total_invoiced = fields.Monetary(
        string='Total Invoiced/Billed',
        compute='_compute_partner_balance',
        currency_field='currency_id',
        help='Total invoiced or billed for this partner',
        store=False
    )

    partner_total_credits = fields.Monetary(
        string='Total Credits',
        compute='_compute_partner_balance',
        currency_field='currency_id',
        help='Total credit notes',
        store=False
    )

    partner_total_paid = fields.Monetary(
        string='Amount Paid',
        compute='_compute_partner_balance',
        currency_field='currency_id',
        help='Total amount paid',
        store=False
    )

    partner_balance_due = fields.Monetary(
        string='Balance Due',
        compute='_compute_partner_balance',
        currency_field='currency_id',
        help='Current receivable/payable balance',
        store=False
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        compute='_compute_currency',
        store=False
    )

    @api.depends('company_id')
    def _compute_currency(self):
        """Get company currency"""
        for picking in self:
            picking.currency_id = picking.company_id.currency_id or self.env.company.currency_id

    @api.depends('partner_id', 'picking_type_id', 'picking_type_id.code')
    def _compute_partner_balance(self):
        """
        Calculate partner financial summary - RESIDUAL METHOD
        For deliveries/receipts, show current receivable/payable position
        """
        for picking in self:
            # Reset values
            picking.partner_total_invoiced = 0.0
            picking.partner_total_credits = 0.0
            picking.partner_total_paid = 0.0
            picking.partner_balance_due = 0.0

            if not picking.partner_id:
                continue

            try:
                # Determine if customer or vendor based on picking type
                if picking.picking_type_id and picking.picking_type_id.code:

                    # Delivery orders (customer)
                    if picking.picking_type_id.code == 'outgoing':
                        invoices = self.env['account.move'].search([
                            ('partner_id', 'child_of', picking.partner_id.commercial_partner_id.id),
                            ('move_type', 'in', ['out_invoice', 'out_refund']),
                            ('state', '=', 'posted')
                        ])

                        out_invoices = invoices.filtered(lambda inv: inv.move_type == 'out_invoice')
                        out_refunds = invoices.filtered(lambda inv: inv.move_type == 'out_refund')

                        total_invoiced = sum(out_invoices.mapped('amount_total'))
                        total_credits = sum(out_refunds.mapped('amount_total'))

                        # RESIDUAL-BASED calculation
                        invoice_residual = sum(out_invoices.mapped('amount_residual'))
                        refund_residual = sum(out_refunds.mapped('amount_residual'))

                        picking.partner_total_invoiced = total_invoiced
                        picking.partner_total_credits = total_credits
                        picking.partner_balance_due = invoice_residual - refund_residual

                        # Get all customer payments
                        payments = self.env['account.payment'].search([
                            ('partner_id', 'child_of', picking.partner_id.commercial_partner_id.id),
                            ('partner_type', '=', 'customer'),
                            ('payment_type', '=', 'inbound'),
                            ('state', 'in', ['posted', 'paid'])
                        ])
                        picking.partner_total_paid = sum(payments.mapped('amount'))

                    # Receipts (vendor)
                    elif picking.picking_type_id.code == 'incoming':
                        bills = self.env['account.move'].search([
                            ('partner_id', 'child_of', picking.partner_id.commercial_partner_id.id),
                            ('move_type', 'in', ['in_invoice', 'in_refund']),
                            ('state', '=', 'posted')
                        ])

                        in_invoices = bills.filtered(lambda bill: bill.move_type == 'in_invoice')
                        in_refunds = bills.filtered(lambda bill: bill.move_type == 'in_refund')

                        total_billed = sum(in_invoices.mapped('amount_total'))
                        total_credits = sum(in_refunds.mapped('amount_total'))

                        # RESIDUAL-BASED calculation
                        bill_residual = sum(in_invoices.mapped('amount_residual'))
                        refund_residual = sum(in_refunds.mapped('amount_residual'))

                        picking.partner_total_invoiced = total_billed
                        picking.partner_total_credits = total_credits
                        picking.partner_balance_due = bill_residual - refund_residual

                        # Get all vendor payments
                        payments = self.env['account.payment'].search([
                            ('partner_id', 'child_of', picking.partner_id.commercial_partner_id.id),
                            ('partner_type', '=', 'supplier'),
                            ('payment_type', '=', 'outbound'),
                            ('state', 'in', ['posted', 'paid'])
                        ])
                        picking.partner_total_paid = sum(payments.mapped('amount'))

                else:
                    # Fallback: determine from location (default to customer)
                    if picking.location_dest_id and picking.location_dest_id.usage == 'customer':
                        # Customer delivery
                        invoices = self.env['account.move'].search([
                            ('partner_id', 'child_of', picking.partner_id.commercial_partner_id.id),
                            ('move_type', 'in', ['out_invoice', 'out_refund']),
                            ('state', '=', 'posted')
                        ])

                        out_invoices = invoices.filtered(lambda inv: inv.move_type == 'out_invoice')
                        out_refunds = invoices.filtered(lambda inv: inv.move_type == 'out_refund')

                        total_invoiced = sum(out_invoices.mapped('amount_total'))
                        total_credits = sum(out_refunds.mapped('amount_total'))

                        invoice_residual = sum(out_invoices.mapped('amount_residual'))
                        refund_residual = sum(out_refunds.mapped('amount_residual'))

                        picking.partner_total_invoiced = total_invoiced
                        picking.partner_total_credits = total_credits
                        picking.partner_balance_due = invoice_residual - refund_residual

                        payments = self.env['account.payment'].search([
                            ('partner_id', 'child_of', picking.partner_id.commercial_partner_id.id),
                            ('partner_type', '=', 'customer'),
                            ('payment_type', '=', 'inbound'),
                            ('state', 'in', ['posted', 'paid'])
                        ])
                        picking.partner_total_paid = sum(payments.mapped('amount'))

                    elif picking.location_id and picking.location_id.usage == 'supplier':
                        # Vendor receipt
                        bills = self.env['account.move'].search([
                            ('partner_id', 'child_of', picking.partner_id.commercial_partner_id.id),
                            ('move_type', 'in', ['in_invoice', 'in_refund']),
                            ('state', '=', 'posted')
                        ])

                        in_invoices = bills.filtered(lambda bill: bill.move_type == 'in_invoice')
                        in_refunds = bills.filtered(lambda bill: bill.move_type == 'in_refund')

                        total_billed = sum(in_invoices.mapped('amount_total'))
                        total_credits = sum(in_refunds.mapped('amount_total'))

                        bill_residual = sum(in_invoices.mapped('amount_residual'))
                        refund_residual = sum(in_refunds.mapped('amount_residual'))

                        picking.partner_total_invoiced = total_billed
                        picking.partner_total_credits = total_credits
                        picking.partner_balance_due = bill_residual - refund_residual

                        payments = self.env['account.payment'].search([
                            ('partner_id', 'child_of', picking.partner_id.commercial_partner_id.id),
                            ('partner_type', '=', 'supplier'),
                            ('payment_type', '=', 'outbound'),
                            ('state', 'in', ['posted', 'paid'])
                        ])
                        picking.partner_total_paid = sum(payments.mapped('amount'))

            except Exception:
                picking.partner_total_invoiced = 0.0
                picking.partner_total_credits = 0.0
                picking.partner_total_paid = 0.0
                picking.partner_balance_due = 0.0

    def action_view_partner_invoices(self):
        """Open partner invoices/bills based on picking type"""
        self.ensure_one()

        if not self.partner_id:
            raise UserError("No partner selected.")

        if self.picking_type_id and self.picking_type_id.code == 'outgoing':
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

    def action_view_partner_credits(self):
        """Open partner credit notes"""
        self.ensure_one()

        if not self.partner_id:
            raise UserError("No partner selected.")

        if self.picking_type_id and self.picking_type_id.code == 'outgoing':
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

    def action_view_partner_payments(self):
        """Open partner payments based on picking type"""
        self.ensure_one()

        if not self.partner_id:
            raise UserError("No partner selected.")

        if self.picking_type_id and self.picking_type_id.code == 'outgoing':
            partner_type = 'customer'
            payment_type = 'inbound'
        else:
            partner_type = 'supplier'
            payment_type = 'outbound'

        return {
            'name': f'Payments - {self.partner_id.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],
            'domain': [
                ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
                ('partner_type', '=', partner_type),
                ('payment_type', '=', payment_type),
                ('state', 'in', ['posted', 'paid'])
            ],
            'context': {
                'create': False,
                'default_partner_id': self.partner_id.id,
                'default_partner_type': partner_type,
                'default_payment_type': payment_type,
            },
        }
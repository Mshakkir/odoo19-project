

from odoo import models, fields, api
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # Partner Balance - Using Accounting Terminology
    partner_total_invoiced = fields.Monetary(
        string='Total Debits',
        compute='_compute_partner_balance',
        currency_field='currency_id',
        help='Total debits (invoices/bills) for this partner',
        store=False
    )

    partner_total_credits = fields.Monetary(
        string='Total Credits',
        compute='_compute_partner_balance',
        currency_field='currency_id',
        help='Total credits (payments + credit notes)',
        store=False
    )

    partner_balance_due = fields.Monetary(
        string='Due Amount',
        compute='_compute_partner_balance',
        currency_field='currency_id',
        help='Outstanding balance (Debits - Credits)',
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
        """Calculate partner financial summary using accounting terminology"""
        for picking in self:
            # Reset values
            picking.partner_total_invoiced = 0.0
            picking.partner_total_credits = 0.0
            picking.partner_balance_due = 0.0

            # Need at least a partner
            if not picking.partner_id:
                continue

            try:
                # If picking_type_id is set, use it to determine customer/vendor
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

                        # Total Debits = All invoices
                        total_debits = sum(out_invoices.mapped('amount_total'))
                        picking.partner_total_invoiced = total_debits

                        # Get all customer payments
                        payments = self.env['account.payment'].search([
                            ('partner_id', 'child_of', picking.partner_id.commercial_partner_id.id),
                            ('partner_type', '=', 'customer'),
                            ('payment_type', '=', 'inbound'),
                            ('state', 'in', ['posted', 'paid'])
                        ])

                        total_payments = sum(payments.mapped('amount'))
                        total_credit_notes = sum(out_refunds.mapped('amount_total'))

                        # Total Credits = Payments + Credit Notes
                        picking.partner_total_credits = total_payments + total_credit_notes

                        # Due Amount = Debits - Credits
                        picking.partner_balance_due = total_debits - (total_payments + total_credit_notes)

                    # Receipts (vendor)
                    elif picking.picking_type_id.code == 'incoming':
                        bills = self.env['account.move'].search([
                            ('partner_id', 'child_of', picking.partner_id.commercial_partner_id.id),
                            ('move_type', 'in', ['in_invoice', 'in_refund']),
                            ('state', '=', 'posted')
                        ])

                        in_invoices = bills.filtered(lambda bill: bill.move_type == 'in_invoice')
                        in_refunds = bills.filtered(lambda bill: bill.move_type == 'in_refund')

                        # Total Debits = All bills
                        total_debits = sum(in_invoices.mapped('amount_total'))
                        picking.partner_total_invoiced = total_debits

                        # Get all vendor payments
                        payments = self.env['account.payment'].search([
                            ('partner_id', 'child_of', picking.partner_id.commercial_partner_id.id),
                            ('partner_type', '=', 'supplier'),
                            ('payment_type', '=', 'outbound'),
                            ('state', 'in', ['posted', 'paid'])
                        ])

                        total_payments = sum(payments.mapped('amount'))
                        total_credit_notes = sum(in_refunds.mapped('amount_total'))

                        # Total Credits = Payments + Credit Notes
                        picking.partner_total_credits = total_payments + total_credit_notes

                        # Due Amount = Debits - Credits
                        picking.partner_balance_due = total_debits - (total_payments + total_credit_notes)

            except Exception:
                picking.partner_total_invoiced = 0.0
                picking.partner_total_credits = 0.0
                picking.partner_balance_due = 0.0

    def action_view_partner_invoices(self):
        """Open partner invoices/bills based on picking type"""
        self.ensure_one()

        if not self.partner_id:
            raise UserError("No partner selected.")

        if self.picking_type_id and self.picking_type_id.code == 'outgoing':
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
            # Vendor bills (or default)
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
        """Open BOTH credit notes AND advance payments - credit entries only"""
        self.ensure_one()

        if not self.partner_id:
            raise UserError("No partner selected.")

        if self.picking_type_id and self.picking_type_id.code == 'outgoing':
            move_types = ['out_refund', 'entry']
            name_prefix = 'Amount Received'
        else:
            move_types = ['in_refund', 'entry']
            name_prefix = 'Amount Paid'

        return {
            'name': f'{name_prefix} (Credit Notes & Advance Payments) - {self.partner_id.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],
            'domain': [
                ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
                ('move_id.state', '=', 'posted'),
                ('move_id.move_type', 'in', move_types),
                ('credit', '>', 0)
            ],
            'context': {'create': False},
        }

    def action_view_partner_payments(self):
        """Open partner payments based on picking type"""
        self.ensure_one()

        if not self.partner_id:
            raise UserError("No partner selected.")

        # Determine partner type and payment type
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
from odoo import models, fields, api
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    partner_total_invoiced = fields.Monetary(
        string='Total Invoiced/Billed',
        compute='_compute_partner_balance',
        currency_field='currency_id',
        help='Total invoiced or billed for this partner'
    )

    partner_total_paid = fields.Monetary(
        string='Amount Paid',
        compute='_compute_partner_balance',
        currency_field='currency_id',
        help='Total amount paid'
    )

    partner_balance_due = fields.Monetary(
        string='Balance Due',
        compute='_compute_partner_balance',
        currency_field='currency_id',
        help='Remaining balance'
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

    @api.depends('partner_id', 'picking_type_id')
    def _compute_partner_balance(self):
        """Calculate partner financial summary based on picking type"""
        for picking in self:
            if picking.partner_id and picking.picking_type_id:
                try:
                    # Delivery orders (customer)
                    if picking.picking_type_id.code == 'outgoing':
                        invoices = self.env['account.move'].search([
                            ('partner_id', 'child_of', picking.partner_id.commercial_partner_id.id),
                            ('move_type', 'in', ['out_invoice', 'out_refund']),
                            ('state', '=', 'posted')
                        ])

                        total_invoiced = sum(invoices.filtered(
                            lambda inv: inv.move_type == 'out_invoice'
                        ).mapped('amount_total'))

                        total_refunded = sum(invoices.filtered(
                            lambda inv: inv.move_type == 'out_refund'
                        ).mapped('amount_total'))

                        total_residual = sum(invoices.mapped('amount_residual'))

                        picking.partner_total_invoiced = total_invoiced - total_refunded
                        picking.partner_balance_due = total_residual
                        picking.partner_total_paid = picking.partner_total_invoiced - picking.partner_balance_due

                    # Receipts (vendor)
                    elif picking.picking_type_id.code == 'incoming':
                        bills = self.env['account.move'].search([
                            ('partner_id', 'child_of', picking.partner_id.commercial_partner_id.id),
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

                        picking.partner_total_invoiced = total_billed - total_refunded
                        picking.partner_balance_due = total_residual
                        picking.partner_total_paid = picking.partner_total_invoiced - picking.partner_balance_due
                    else:
                        picking.partner_total_invoiced = 0.0
                        picking.partner_total_paid = 0.0
                        picking.partner_balance_due = 0.0

                except Exception:
                    picking.partner_total_invoiced = 0.0
                    picking.partner_total_paid = 0.0
                    picking.partner_balance_due = 0.0
            else:
                picking.partner_total_invoiced = 0.0
                picking.partner_total_paid = 0.0
                picking.partner_balance_due = 0.0

    def action_view_partner_invoices(self):
        """Open partner invoices/bills based on picking type"""
        self.ensure_one()

        if not self.partner_id:
            raise UserError("No partner selected.")

        if self.picking_type_id.code == 'outgoing':
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
            # Vendor bills
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

    def action_view_partner_payments(self):
        """Open partner payments based on picking type"""
        self.ensure_one()

        if not self.partner_id:
            raise UserError("No partner selected.")

        all_payments = self.env['account.payment'].search([
            ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
        ])

        payment_type = 'inbound' if self.picking_type_id.code == 'outgoing' else 'outbound'

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
                ('payment_type', '=', payment_type),
            ],
            'context': {
                'create': False,
                'default_partner_id': self.partner_id.id,
                'default_payment_type': payment_type,
            },
        }
from odoo import models, fields, api
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    customer_total_invoiced = fields.Monetary(
        string='Total Invoiced',
        compute='_compute_customer_balance',
        currency_field='currency_id',
        help='Click to view all customer invoices'
    )

    customer_total_paid = fields.Monetary(
        string='Amount Paid',
        compute='_compute_customer_balance',
        currency_field='currency_id',
        help='Click to view all customer payments'
    )

    customer_balance_due = fields.Monetary(
        string='Balance Due',
        compute='_compute_customer_balance',
        currency_field='currency_id',
        help='Remaining balance (Total Invoiced - Amount Paid)'
    )

    @api.depends('partner_id')
    def _compute_customer_balance(self):
        """Calculate customer financial summary"""
        for order in self:
            if order.partner_id:
                try:
                    invoices = self.env['account.move'].search([
                        ('partner_id', 'child_of', order.partner_id.commercial_partner_id.id),
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

                    order.customer_total_invoiced = total_invoiced - total_refunded
                    order.customer_balance_due = total_residual
                    order.customer_total_paid = order.customer_total_invoiced - order.customer_balance_due
                except:
                    order.customer_total_invoiced = 0.0
                    order.customer_total_paid = 0.0
                    order.customer_balance_due = 0.0
            else:
                order.customer_total_invoiced = 0.0
                order.customer_total_paid = 0.0
                order.customer_balance_due = 0.0

    def action_view_customer_invoices(self):
        """Open filtered list of customer invoices"""
        self.ensure_one()

        if not self.partner_id:
            raise UserError("Please select a customer first.")

        # Search for invoices
        invoices = self.env['account.move'].search([
            ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('state', '=', 'posted')
        ])

        if not invoices:
            raise UserError(f"No invoices found for {self.partner_id.name}")

        # Return proper action with all required fields
        return {
            'name': f'Invoices - {self.partner_id.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'tree,form',  # REQUIRED field
            'views': [(False, 'tree'), (False, 'form')],  # Let Odoo find default views
            'domain': [('id', 'in', invoices.ids)],
            'context': {
                'create': False,
                'edit': False,
                'default_move_type': 'out_invoice',
            },
            'target': 'current',  # Changed to current for better compatibility
        }

    def action_view_customer_invoices(self):
        """Open filtered list of customer invoices"""
        self.ensure_one()

        if not self.partner_id:
            raise UserError("Please select a customer first.")

        # Search for invoices
        domain = [
            ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('state', '=', 'posted')
        ]

        invoices = self.env['account.move'].search(domain)

        # Return action even if no invoices (shows empty list)
        return {
            'name': f'Invoices - {self.partner_id.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': domain,  # Use domain instead of ids for better performance
            'context': {
                'create': False,
                'default_move_type': 'out_invoice',
            },
            'target': 'current',
        }
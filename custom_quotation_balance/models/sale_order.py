from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    customer_balance_due = fields.Monetary(
        string='Balance Due',
        compute='_compute_customer_balance',
        currency_field='currency_id',
        help='Total amount customer owes (unpaid invoices)'
    )

    customer_total_paid = fields.Monetary(
        string='Total Paid',
        compute='_compute_customer_balance',
        currency_field='currency_id',
        help='Total amount customer has paid'
    )

    customer_total_invoiced = fields.Monetary(
        string='Total Invoiced',
        compute='_compute_customer_balance',
        currency_field='currency_id',
        help='Total invoiced amount for this customer'
    )

    @api.depends('partner_id')
    def _compute_customer_balance(self):
        for order in self:
            if order.partner_id:
                # Get all invoices for this customer
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
            else:
                order.customer_balance_due = 0.0
                order.customer_total_paid = 0.0
                order.customer_total_invoiced = 0.0
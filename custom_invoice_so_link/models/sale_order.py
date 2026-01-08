from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Add a custom computed field to track invoices created via your custom method
    custom_invoice_ids = fields.Many2many(
        'account.move',
        compute='_compute_custom_invoice_ids',
        string='Custom Invoices'
    )

    custom_invoice_count = fields.Integer(
        compute='_compute_custom_invoice_ids',
        string='Custom Invoice Count'
    )

    @api.depends('name')
    def _compute_custom_invoice_ids(self):
        """Find all invoices linked to this SO via sale_order_id field"""
        for order in self:
            invoices = self.env['account.move'].search([
                ('sale_order_id', '=', order.id),
                ('move_type', 'in', ['out_invoice', 'out_refund']),
                ('state', '!=', 'cancel')
            ])
            order.custom_invoice_ids = invoices
            order.custom_invoice_count = len(invoices)
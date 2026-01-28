from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Add a field to check if invoices are linked from account move
    is_invoice_created_from_module = fields.Boolean(
        string='Invoice Created via Sales Order Link',
        help="Indicates if invoice was created using the Invoice Sales Order Link module",
        default=False
    )

    @api.depends('invoice_ids')
    def _compute_invoice_status(self):
        """Override to add custom logic for invoice status"""
        super()._compute_invoice_status()
        # This allows the standard flow to work while our custom module manages invoicing differently
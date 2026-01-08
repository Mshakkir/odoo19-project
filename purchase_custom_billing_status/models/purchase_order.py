from odoo import models, fields, api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # Override the selection to add custom labels
    invoice_status = fields.Selection(
        selection=[
            ('no', 'No Invoice Required'),
            ('to invoice', 'Waiting Bills'),
            ('partially_invoice', 'Partially Billed'),
            ('invoiced', 'Fully Billed'),
        ],
        string='Billing Status',
        compute='_compute_invoice_status',
        store=True,
        readonly=True,
    )

    @api.depends('order_line.qty_received', 'order_line.qty_invoiced', 'order_line.product_qty', 'state')
    def _compute_invoice_status(self):
        """
        Compute the invoice status based on order lines invoiced quantity
        """
        for order in self:
            # If order is not in purchase state, no invoice status
            if order.state != 'purchase':
                order.invoice_status = 'no'
                continue

            # Get all lines that require invoicing (product type goods only)
            lines = order.order_line.filtered(lambda x: x.product_id.type in ['consu', 'product'])

            if not lines:
                order.invoice_status = 'no'
                continue

            # Calculate quantities
            total_qty = sum(lines.mapped('product_qty'))
            invoiced_qty = sum(lines.mapped('qty_invoiced'))

            if invoiced_qty == 0:
                # No lines invoiced
                order.invoice_status = 'to invoice'
            elif invoiced_qty >= total_qty:
                # All lines invoiced
                order.invoice_status = 'invoiced'
            else:
                # Some lines invoiced, not all
                order.invoice_status = 'partially_invoice'
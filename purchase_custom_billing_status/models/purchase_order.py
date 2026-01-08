from odoo import models, fields, api

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    invoice_status = fields.Selection(
        selection=[
            ('no', 'No Invoice'),
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
        Compute the invoice status of PO based on invoiced quantity
        """
        for order in self:
            # If order is not in purchase or done state, set to no
            if order.state not in ['purchase', 'done']:
                order.invoice_status = 'no'
                continue

            # Filter lines that need invoicing (exclude services without purchase order)
            invoice_lines = order.order_line.filtered(
                lambda x: x.product_id.type != 'service'
            )

            if not invoice_lines:
                order.invoice_status = 'no'
                continue

            # Calculate total and invoiced quantities
            total_qty = sum(line.product_qty for line in invoice_lines)
            invoiced_qty = sum(line.qty_invoiced for line in invoice_lines)

            if total_qty == 0:
                order.invoice_status = 'no'
            elif invoiced_qty == 0:
                # Nothing invoiced yet
                order.invoice_status = 'to invoice'
            elif invoiced_qty >= total_qty:
                # Everything invoiced
                order.invoice_status = 'invoiced'
            else:
                # Partially invoiced
                order.invoice_status = 'partially_invoice'
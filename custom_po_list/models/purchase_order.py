from odoo import models, fields, api


class PurchaseOrderExtended(models.Model):
    _inherit = 'purchase.order'

    partially_billed_amount = fields.Monetary(
        string='Partially Billed Amount',
        compute='_compute_partially_billed_amount',
        store=False,
        currency_field='currency_id'
    )

    partially_billed_status = fields.Selection(
        [('not_billed', 'Not Billed'),
         ('partially_billed', 'Partially Billed'),
         ('fully_billed', 'Fully Billed')],
        string='Billed Status',
        compute='_compute_billed_status',
        store=False
    )

    @api.depends('invoice_ids', 'amount_total')
    def _compute_partially_billed_amount(self):
        """Calculate the partially billed amount based on invoice lines"""
        for record in self:
            billed_amount = 0.0

            # Get all invoices related to this PO
            invoices = record.invoice_ids.filtered(
                lambda x: x.state in ['posted', 'paid']
            )

            if invoices:
                for invoice in invoices:
                    # Sum invoice line amounts
                    billed_amount += invoice.amount_total

            record.partially_billed_amount = billed_amount

    @api.depends('invoice_ids', 'amount_total', 'partially_billed_amount')
    def _compute_billed_status(self):
        """Determine the billing status of the PO"""
        for record in self:
            total = record.amount_total
            billed = record.partially_billed_amount

            if billed == 0:
                record.partially_billed_status = 'not_billed'
            elif billed >= total:
                record.partially_billed_status = 'fully_billed'
            else:
                record.partially_billed_status = 'partially_billed'
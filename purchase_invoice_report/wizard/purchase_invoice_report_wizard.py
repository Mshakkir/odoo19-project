from odoo import models, fields, api


class PurchaseInvoiceReportWizard(models.TransientModel):
    _name = 'purchase.invoice.report.wizard'
    _description = 'Purchase Invoice Report Wizard'

    date_from = fields.Date(
        string='Date From',
        required=True,
        default=fields.Date.context_today
    )
    date_to = fields.Date(
        string='Date To',
        required=True,
        default=fields.Date.context_today
    )
    invoice_ids = fields.Many2many(
        'account.move',
        string='Invoice Numbers',
        required=True,
        domain=[('move_type', '=', 'in_invoice'), ('state', '=', 'posted')]
    )

    def action_show_report(self):
        """Open the report view with filtered data"""
        self.ensure_one()

        # Create the report records
        report_obj = self.env['purchase.invoice.report']

        # Clear existing report data first
        report_obj.search([]).unlink()

        # Search for purchase invoices matching criteria
        domain = [
            ('id', 'in', self.invoice_ids.ids),
            ('move_type', '=', 'in_invoice'),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
        ]

        invoices = self.env['account.move'].search(domain)

        # Create report records from invoice lines
        for invoice in invoices:
            # Get warehouse from invoice lines (first line with warehouse)
            warehouse_id = False
            for line in invoice.invoice_line_ids:
                if hasattr(line, 'warehouse_id') and line.warehouse_id:
                    warehouse_id = line.warehouse_id.id
                    break

            # If not found in lines, try to get from purchase order
            if not warehouse_id and invoice.invoice_origin:
                purchase_order = self.env['purchase.order'].search([
                    ('name', '=', invoice.invoice_origin)
                ], limit=1)
                if purchase_order and purchase_order.picking_type_id:
                    warehouse_id = purchase_order.picking_type_id.warehouse_id.id

            # Process each invoice line
            for line in invoice.invoice_line_ids:
                if line.product_id:  # Only lines with products
                    report_obj.create({
                        'invoice_date': invoice.invoice_date,
                        'invoice_number': invoice.name,
                        'vendor_id': invoice.partner_id.id,
                        'warehouse_id': warehouse_id,
                        'product_id': line.product_id.id,
                        'quantity': line.quantity,
                        'uom_id': line.product_uom_id.id,
                        'price_unit': line.price_unit,
                        'net_amount': line.price_total,  # Includes tax
                    })

        # Return action to open list view
        return {
            'name': 'Purchase Invoice Report',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.invoice.report',
            'view_mode': 'list',
            'view_id': self.env.ref('purchase_invoice_report.view_purchase_invoice_report_list').id,
            'target': 'current',
            'domain': [],
        }
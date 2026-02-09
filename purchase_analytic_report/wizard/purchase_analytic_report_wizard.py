from odoo import models, fields, api


class PurchaseAnalyticReportWizard(models.TransientModel):
    _name = 'purchase.analytic.report.wizard'
    _description = 'Purchase Analytic Report Wizard'

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
    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        string='Analytic Accounts',
        required=True
    )

    def action_show_report(self):
        """Open the report view with filtered data"""
        self.ensure_one()

        # Create the report records
        report_obj = self.env['purchase.analytic.report']

        # Clear existing report data first
        report_obj.search([]).unlink()

        # Search for purchase invoices matching criteria
        domain = [
            ('move_type', '=', 'in_invoice'),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
        ]

        invoices = self.env['account.move'].search(domain)

        # Create report records from invoice lines that have matching analytic accounts
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

            # Process each invoice line with analytic distribution
            for line in invoice.invoice_line_ids:
                if line.product_id and line.analytic_distribution:
                    # Check if any of the selected analytic accounts are in this line
                    analytic_account_ids = [int(k) for k in line.analytic_distribution.keys()]

                    # Find matching analytic accounts
                    matching_analytics = list(set(analytic_account_ids) & set(self.analytic_account_ids.ids))

                    if matching_analytics:
                        # Create a report line for each matching analytic account
                        for analytic_id in matching_analytics:
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
                                'analytic_account_id': analytic_id,
                            })

        # Return action to open list view
        return {
            'name': 'Purchase Analytic Report',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.analytic.report',
            'view_mode': 'list',
            'view_id': self.env.ref('purchase_analytic_report.view_purchase_analytic_report_list').id,
            # 'target': 'current',
            'target': 'new',
            'domain': [],
        }
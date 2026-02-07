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

        # Search for purchase invoices matching criteria
        domain = [
            ('move_type', '=', 'in_invoice'),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
        ]

        invoices = self.env['account.move'].search(domain)

        # Clear existing report data
        report_obj.search([]).unlink()

        # Create report records - one per invoice line with analytic account
        for invoice in invoices:
            # Get warehouse from purchase order or invoice lines
            warehouse_id = False
            if invoice.invoice_origin:
                purchase_order = self.env['purchase.order'].search([
                    ('name', '=', invoice.invoice_origin)
                ], limit=1)
                if purchase_order and purchase_order.picking_type_id:
                    warehouse_id = purchase_order.picking_type_id.warehouse_id.id

            # Process each invoice line
            for line in invoice.invoice_line_ids:
                # Check if line has analytic distribution
                if line.analytic_distribution:
                    # Get analytic account IDs from distribution
                    line_analytic_ids = [int(k) for k in line.analytic_distribution.keys()]

                    # Check if any of the line's analytic accounts match our filter
                    matching_analytic = set(line_analytic_ids) & set(self.analytic_account_ids.ids)

                    if matching_analytic:
                        # Use the first matching analytic account
                        analytic_account_id = list(matching_analytic)[0]

                        # Get warehouse from line if available
                        line_warehouse_id = warehouse_id
                        if hasattr(line, 'warehouse_id') and line.warehouse_id:
                            line_warehouse_id = line.warehouse_id.id

                        # Calculate net amount for this line
                        net_amount = line.price_subtotal

                        report_obj.create({
                            'invoice_date': invoice.invoice_date,
                            'invoice_number': invoice.name,
                            'vendor_id': invoice.partner_id.id,
                            'warehouse_id': line_warehouse_id,
                            'product_id': line.product_id.id if line.product_id else False,
                            'quantity': line.quantity,
                            'uom_id': line.product_uom_id.id if line.product_uom_id else False,
                            'unit_price': line.price_unit,
                            'net_amount': net_amount,
                            'analytic_account_id': analytic_account_id,
                        })

        # Return action to open list view
        return {
            'name': 'Purchase Analytic Report',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.analytic.report',
            'view_mode': 'tree',
            'view_id': self.env.ref('purchase_analytic_report.view_purchase_analytic_report_tree').id,
            'target': 'current',
            'domain': [],
        }
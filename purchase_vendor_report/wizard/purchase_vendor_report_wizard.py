from odoo import models, fields, api


class PurchaseVendorReportWizard(models.TransientModel):
    _name = 'purchase.vendor.report.wizard'
    _description = 'Purchase Vendor Report Wizard'

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
    vendor_ids = fields.Many2many(
        'res.partner',
        string='Vendors',
        required=True,
        domain=[('supplier_rank', '>', 0)]
    )

    def action_show_report(self):
        """Open the report view with filtered data"""
        self.ensure_one()

        # Create the report records
        report_obj = self.env['purchase.vendor.report']

        # Search for purchase invoices matching criteria
        domain = [
            ('move_type', '=', 'in_invoice'),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
            ('partner_id', 'in', self.vendor_ids.ids),
        ]

        invoices = self.env['account.move'].search(domain)

        # Clear existing report data
        report_obj.search([]).unlink()

        # Create report records
        for invoice in invoices:
            # Get warehouse from purchase order if exists
            warehouse_id = False
            purchase_order = self.env['purchase.order'].search([
                ('name', '=', invoice.invoice_origin)
            ], limit=1)
            if purchase_order:
                warehouse_id = purchase_order.picking_type_id.warehouse_id.id

            # Get analytic account from invoice lines (first one found)
            analytic_account_id = False
            for line in invoice.invoice_line_ids:
                if line.analytic_distribution:
                    # Get the first analytic account from distribution
                    analytic_account_ids = [int(k) for k in line.analytic_distribution.keys()]
                    if analytic_account_ids:
                        analytic_account_id = analytic_account_ids[0]
                        break

            # Get purchase account from invoice lines (first product line)
            purchase_account_id = False
            for line in invoice.invoice_line_ids:
                if line.product_id and line.account_id:
                    purchase_account_id = line.account_id.id
                    break

            report_obj.create({
                'invoice_date': invoice.invoice_date,
                'invoice_number': invoice.name,
                'vendor_id': invoice.partner_id.id,
                'analytic_account_id': analytic_account_id,
                'purchase_account_id': purchase_account_id,
                'warehouse_id': warehouse_id,
                'net_amount': invoice.amount_untaxed,
            })

        # Return action to open list view
        return {
            'name': 'Purchase Vendor Report',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.vendor.report',
            'view_mode': 'list',
            'view_id': self.env.ref('purchase_vendor_report.view_purchase_vendor_report_list').id,
            'target': 'current',
            'domain': [],
        }
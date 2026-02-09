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
    all_vendors = fields.Boolean(
        string='All Vendors',
        default=False
    )
    vendor_ids = fields.Many2many(
        'res.partner',
        string='Vendors',
        domain=[('supplier_rank', '>', 0)]
    )
    invoice_status = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancel', 'Cancelled'),
        ('all', 'All')
    ], string='Invoice Status', default='all', required=True)

    @api.onchange('all_vendors')
    def _onchange_all_vendors(self):
        """When All Vendors is checked, clear vendor selection"""
        if self.all_vendors:
            self.vendor_ids = [(5, 0, 0)]

    def action_show_report(self):
        """Open the report view with filtered data"""
        self.ensure_one()

        # Validate: either all_vendors is checked OR vendors are selected
        if not self.all_vendors and not self.vendor_ids:
            raise models.ValidationError('Please select vendors or check "All Vendors"')

        # Create the report records
        report_obj = self.env['purchase.vendor.report']

        # Clear existing report data
        report_obj.search([]).unlink()

        # Search for purchase invoices matching criteria
        domain = [
            ('move_type', '=', 'in_invoice'),
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
        ]

        # Add vendor filter only if not "All Vendors"
        if not self.all_vendors:
            domain.append(('partner_id', 'in', self.vendor_ids.ids))

        # Add state filter based on selection
        if self.invoice_status == 'draft':
            domain.append(('state', '=', 'draft'))
        elif self.invoice_status == 'posted':
            domain.append(('state', '=', 'posted'))
        elif self.invoice_status == 'cancel':
            domain.append(('state', '=', 'cancel'))

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
                    # Get analytic account from line
                    analytic_account_id = False
                    if line.analytic_distribution:
                        analytic_account_ids = [int(k) for k in line.analytic_distribution.keys()]
                        if analytic_account_ids:
                            analytic_account_id = analytic_account_ids[0]

                    # Get buyer from invoice
                    buyer_id = invoice.buyer_id.id if invoice.buyer_id else False

                    # Calculate discount (fixed)
                    discount = line.discount_fixed if hasattr(line, 'discount_fixed') else 0.0

                    # Calculate untaxed amount (subtotal)
                    untaxed_amount = line.price_subtotal if hasattr(line, 'price_subtotal') else 0.0

                    # Calculate tax value
                    tax_value = line.tax_amount if hasattr(line, 'tax_amount') else 0.0

                    report_obj.create({
                        'invoice_date': invoice.invoice_date,
                        'invoice_number': invoice.name,
                        'analytic_account_id': analytic_account_id,
                        'vendor_id': invoice.partner_id.id,
                        'warehouse_id': warehouse_id,
                        'product_id': line.product_id.id,
                        'buyer_id': buyer_id,
                        'quantity': line.quantity,
                        'uom_id': line.product_uom_id.id,
                        'price_unit': line.price_unit,
                        'discount': discount,
                        'untaxed_amount': untaxed_amount,
                        'tax_value': tax_value,
                        'net_amount': line.price_total,
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
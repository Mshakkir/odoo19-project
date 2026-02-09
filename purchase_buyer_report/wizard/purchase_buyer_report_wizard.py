from odoo import models, fields, api


class PurchaseBuyerReportWizard(models.TransientModel):
    _name = 'purchase.buyer.report.wizard'
    _description = 'Purchase Buyer Report Wizard'

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
    all_buyers = fields.Boolean(
        string='All Buyers',
        default=False
    )
    buyer_ids = fields.Many2many(
        'res.users',
        string='Buyers'
    )
    invoice_status = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancel', 'Cancelled'),
        ('all', 'All')
    ], string='Invoice Status', default='all', required=True)

    @api.onchange('all_buyers')
    def _onchange_all_buyers(self):
        """When All Buyers is checked, clear buyer selection"""
        if self.all_buyers:
            self.buyer_ids = [(5, 0, 0)]

    def action_show_report(self):
        """Open the report view with filtered data"""
        self.ensure_one()

        # Validate: either all_buyers is checked OR buyers are selected
        if not self.all_buyers and not self.buyer_ids:
            raise models.ValidationError('Please select buyers or check "All Buyers"')

        # Create the report records
        report_obj = self.env['purchase.buyer.report']

        # Clear existing report data first
        report_obj.search([]).unlink()

        # Search for purchase invoices with buyer_id matching criteria
        domain = [
            ('move_type', '=', 'in_invoice'),
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
        ]

        # Add buyer filter only if not "All Buyers"
        if not self.all_buyers:
            domain.append(('buyer_id', 'in', self.buyer_ids.ids))

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
            # Get warehouse from invoice lines or purchase order
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

            for line in invoice.invoice_line_ids:
                if line.product_id:  # Only lines with products
                    # Get analytic account from line
                    analytic_account_id = False
                    if line.analytic_distribution:
                        analytic_account_ids = [int(k) for k in line.analytic_distribution.keys()]
                        if analytic_account_ids:
                            analytic_account_id = analytic_account_ids[0]

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
                        'buyer_id': invoice.buyer_id.id if invoice.buyer_id else False,
                        'vendor_id': invoice.partner_id.id,
                        'warehouse_id': warehouse_id,
                        'product_id': line.product_id.id,
                        'quantity': line.quantity,
                        'uom_id': line.product_uom_id.id,
                        'price_unit': line.price_unit,
                        'discount': discount,
                        'untaxed_amount': untaxed_amount,
                        'tax_value': tax_value,
                        'net_amount': line.price_total,  # Includes tax
                    })

        # Return action to open list view
        return {
            'name': 'Purchase Buyer Report',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.buyer.report',
            'view_mode': 'list',
            'view_id': self.env.ref('purchase_buyer_report.view_purchase_buyer_report_list').id,
            'target': 'current',
            'domain': [],
        }
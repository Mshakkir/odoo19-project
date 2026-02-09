from odoo import models, fields, api


class PurchaseProductReportWizard(models.TransientModel):
    _name = 'purchase.product.report.wizard'
    _description = 'Purchase Product Report Wizard'

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
    all_products = fields.Boolean(
        string='All Products',
        default=False
    )
    product_ids = fields.Many2many(
        'product.product',
        string='Products'
    )
    invoice_status = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancel', 'Cancelled'),
        ('all', 'All')
    ], string='Invoice Status', default='all', required=True)

    @api.onchange('all_products')
    def _onchange_all_products(self):
        """When All Products is checked, clear product selection"""
        if self.all_products:
            self.product_ids = [(5, 0, 0)]  # Clear all products

    def action_show_report(self):
        """Open the report view with filtered data"""
        self.ensure_one()

        # Validate: either all_products is checked OR products are selected
        if not self.all_products and not self.product_ids:
            raise models.ValidationError('Please select products or check "All Products"')

        # Create the report records
        report_obj = self.env['purchase.bypd.report']

        # Build domain based on invoice status
        domain = [
            ('move_id.move_type', '=', 'in_invoice'),
            ('move_id.invoice_date', '>=', self.date_from),
            ('move_id.invoice_date', '<=', self.date_to),
        ]

        # Add product filter only if not "All Products"
        if not self.all_products:
            domain.append(('product_id', 'in', self.product_ids.ids))

        # Add state filter based on selection
        if self.invoice_status == 'draft':
            domain.append(('move_id.state', '=', 'draft'))
        elif self.invoice_status == 'posted':
            domain.append(('move_id.state', '=', 'posted'))
        elif self.invoice_status == 'cancel':
            domain.append(('move_id.state', '=', 'cancel'))
        # If 'all', don't add state filter

        invoice_lines = self.env['account.move.line'].search(domain)

        # Clear existing report data
        report_obj.search([]).unlink()

        # Create report records
        for line in invoice_lines:
            if line.product_id:
                # Get analytic account from line
                analytic_account_id = False
                if line.analytic_distribution:
                    # analytic_distribution is a JSON field with analytic_account_id as keys
                    analytic_ids = list(line.analytic_distribution.keys())
                    if analytic_ids:
                        analytic_account_id = int(analytic_ids[0])

                # Get warehouse from invoice line
                warehouse_id = line.warehouse_id.id if line.warehouse_id else False

                # Get buyer from purchase order (via invoice)
                buyer_id = False
                if line.move_id.invoice_origin:
                    # Try to find purchase order from origin
                    purchase_order = self.env['purchase.order'].search([
                        ('name', '=', line.move_id.invoice_origin)
                    ], limit=1)
                    if purchase_order:
                        buyer_id = purchase_order.user_id.id

                # Calculate tax amount
                tax_amount = 0
                if line.tax_ids:
                    tax_amount = line.price_total - line.price_subtotal

                report_obj.create({
                    'invoice_date': line.move_id.invoice_date,
                    'invoice_number': line.move_id.name,
                    'analytic_account_id': analytic_account_id,
                    'vendor_id': line.move_id.partner_id.id,
                    'warehouse_id': warehouse_id,
                    'product_id': line.product_id.id,
                    'buyer_id': buyer_id,
                    'quantity': line.quantity,
                    'uom_id': line.product_uom_id.id,
                    'price_unit': line.price_unit,
                    'price_total': line.price_total,
                    'discount_fixed': line.discount_fixed if hasattr(line, 'discount_fixed') else 0,
                    'price_subtotal': line.price_subtotal,
                    'tax_amount': tax_amount,
                })

        # Return action to open list view
        return {
            'name': 'Purchase Product Report',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.bypd.report',
            'view_mode': 'list',
            'view_id': self.env.ref('purchase_bypd_report.view_purchase_bypd_report_list').id,
            'target': 'current',
            'domain': [],
        }
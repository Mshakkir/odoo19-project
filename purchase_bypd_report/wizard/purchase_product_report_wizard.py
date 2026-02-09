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
                report_obj.create({
                    'invoice_date': line.move_id.invoice_date,
                    'invoice_number': line.move_id.name,
                    'product_id': line.product_id.id,
                    'quantity': line.quantity,
                    'uom_id': line.product_uom_id.id,
                    'price_unit': line.price_unit,
                    'price_total': line.price_total,
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


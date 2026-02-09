from odoo import models, fields, api


class PurchaseProductCategoryReportWizard(models.TransientModel):
    _name = 'purchase.product.category.report.wizard'
    _description = 'Purchase Product Category Report Wizard'

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
    all_categories = fields.Boolean(
        string='All Product Categories',
        default=False
    )
    product_category_ids = fields.Many2many(
        'product.category',
        string='Product Categories'
    )
    invoice_status = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancel', 'Cancelled'),
        ('all', 'All')
    ], string='Invoice Status', default='all', required=True)

    @api.onchange('all_categories')
    def _onchange_all_categories(self):
        """When All Product Categories is checked, clear category selection"""
        if self.all_categories:
            self.product_category_ids = [(5, 0, 0)]

    def action_show_report(self):
        """Open the report view with filtered data"""
        self.ensure_one()

        # Validate: either all_categories is checked OR categories are selected
        if not self.all_categories and not self.product_category_ids:
            raise models.ValidationError('Please select product categories or check "All Product Categories"')

        # Create the report records
        report_obj = self.env['purchase.product.category.report']

        # Clear existing report data first
        report_obj.search([]).unlink()

        # Search for purchase invoices matching criteria
        domain = [
            ('move_type', '=', 'in_invoice'),
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
        ]

        # Add state filter based on selection
        if self.invoice_status == 'draft':
            domain.append(('state', '=', 'draft'))
        elif self.invoice_status == 'posted':
            domain.append(('state', '=', 'posted'))
        elif self.invoice_status == 'cancel':
            domain.append(('state', '=', 'cancel'))

        invoices = self.env['account.move'].search(domain)

        # Create report records from invoice lines filtered by product category
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

            # Get buyer from purchase order
            buyer_id = False
            if invoice.invoice_origin:
                purchase_order = self.env['purchase.order'].search([
                    ('name', '=', invoice.invoice_origin)
                ], limit=1)
                if purchase_order and purchase_order.user_id:
                    buyer_id = purchase_order.user_id.id

            # Process each invoice line
            for line in invoice.invoice_line_ids:
                if line.product_id and line.product_id.categ_id:
                    product_category_id = line.product_id.categ_id.id
                    
                    # Check if this product category should be included
                    if self.all_categories:
                        should_include = True
                    else:
                        # Check if product category is in selected categories
                        # Also check parent categories recursively
                        category = line.product_id.categ_id
                        should_include = False
                        while category:
                            if category.id in self.product_category_ids.ids:
                                should_include = True
                                break
                            category = category.parent_id
                    
                    if should_include:
                        # Get analytic account if exists
                        analytic_id = False
                        if line.analytic_distribution:
                            analytic_account_ids = [int(k) for k in line.analytic_distribution.keys()]
                            if analytic_account_ids:
                                analytic_id = analytic_account_ids[0]  # Take first analytic account
                        
                        # Calculate discount (fixed discount from line)
                        discount = line.discount_fixed if hasattr(line, 'discount_fixed') else 0.0
                        
                        # Calculate untaxed amount (price_subtotal)
                        untaxed_amount = line.price_subtotal
                        
                        # Calculate tax value (difference between total and subtotal)
                        tax_value = line.price_total - line.price_subtotal
                        
                        report_obj.create({
                            'invoice_date': invoice.invoice_date,
                            'invoice_number': invoice.name,
                            'vendor_id': invoice.partner_id.id,
                            'warehouse_id': warehouse_id,
                            'buyer_id': buyer_id,
                            'product_category_id': product_category_id,
                            'product_id': line.product_id.id,
                            'quantity': line.quantity,
                            'uom_id': line.product_uom_id.id,
                            'price_unit': line.price_unit,
                            'discount': discount,
                            'untaxed_amount': untaxed_amount,
                            'tax_value': tax_value,
                            'net_amount': line.price_total,  # Includes tax
                            'analytic_account_id': analytic_id,
                        })

        # Return action to open list view
        return {
            'name': 'Purchase Product Category Report',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.product.category.report',
            'view_mode': 'list',
            'view_id': self.env.ref('purchase_product_category_report.view_purchase_product_category_report_list').id,
            'target': 'current',
            'domain': [],
        }

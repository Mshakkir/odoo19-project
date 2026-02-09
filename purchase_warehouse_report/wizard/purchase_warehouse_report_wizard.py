from odoo import models, fields, api


class PurchaseWarehouseReportWizard(models.TransientModel):
    _name = 'purchase.warehouse.report.wizard'
    _description = 'Purchase Warehouse Report Wizard'

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
    all_warehouses = fields.Boolean(
        string='All Warehouses',
        default=False
    )
    warehouse_ids = fields.Many2many(
        'stock.warehouse',
        string='Warehouses'
    )
    invoice_status = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancel', 'Cancelled'),
        ('all', 'All')
    ], string='Invoice Status', default='all', required=True)

    @api.onchange('all_warehouses')
    def _onchange_all_warehouses(self):
        """When All Warehouses is checked, clear warehouse selection"""
        if self.all_warehouses:
            self.warehouse_ids = [(5, 0, 0)]

    def action_show_report(self):
        """Open the report view with filtered data"""
        self.ensure_one()

        # Validate: either all_warehouses is checked OR warehouses are selected
        if not self.all_warehouses and not self.warehouse_ids:
            raise models.ValidationError('Please select warehouses or check "All Warehouses"')

        # Create the report records
        report_obj = self.env['purchase.warehouse.report']

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

        # Create report records from invoice lines filtered by warehouse
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

            # Check if this warehouse should be included
            if warehouse_id:
                # If "All Warehouses" is selected, include all
                if self.all_warehouses:
                    should_include = True
                else:
                    # Check if warehouse is in selected warehouses
                    should_include = warehouse_id in self.warehouse_ids.ids
                
                if should_include:
                    # Process each invoice line
                    for line in invoice.invoice_line_ids:
                        if line.product_id:
                            # Get analytic account if exists
                            analytic_id = False
                            if line.analytic_distribution:
                                analytic_account_ids = [int(k) for k in line.analytic_distribution.keys()]
                                if analytic_account_ids:
                                    analytic_id = analytic_account_ids[0]  # Take first analytic account
                            
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
            'name': 'Purchase Warehouse Report',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.warehouse.report',
            'view_mode': 'list',
            'view_id': self.env.ref('purchase_warehouse_report.view_purchase_warehouse_report_list').id,
            'target': 'current',
            'domain': [],
        }

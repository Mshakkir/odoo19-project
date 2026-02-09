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

        # Create report records
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

            # Get analytic account from invoice lines (first one found)
            analytic_account_id = False
            for line in invoice.invoice_line_ids:
                if line.analytic_distribution:
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
                'net_amount': invoice.amount_total,
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













# from odoo import models, fields, api
#
#
# class PurchaseVendorReportWizard(models.TransientModel):
#     _name = 'purchase.vendor.report.wizard'
#     _description = 'Purchase Vendor Report Wizard'
#
#     date_from = fields.Date(
#         string='Date From',
#         required=True,
#         default=fields.Date.context_today
#     )
#     date_to = fields.Date(
#         string='Date To',
#         required=True,
#         default=fields.Date.context_today
#     )
#     vendor_ids = fields.Many2many(
#         'res.partner',
#         string='Vendors',
#         required=True,
#         domain=[('supplier_rank', '>', 0)]
#     )
#
#     def action_show_report(self):
#         """Open the report view with filtered data"""
#         self.ensure_one()
#
#         # Create the report records
#         report_obj = self.env['purchase.vendor.report']
#
#         # Search for purchase invoices matching criteria
#         domain = [
#             ('move_type', '=', 'in_invoice'),
#             ('state', '=', 'posted'),
#             ('invoice_date', '>=', self.date_from),
#             ('invoice_date', '<=', self.date_to),
#             ('partner_id', 'in', self.vendor_ids.ids),
#         ]
#
#         invoices = self.env['account.move'].search(domain)
#
#         # Clear existing report data
#         report_obj.search([]).unlink()
#
#         # Create report records - one per invoice (not per line)
#         for invoice in invoices:
#             # Get warehouse from invoice lines (first line with warehouse)
#             warehouse_id = False
#             for line in invoice.invoice_line_ids:
#                 if hasattr(line, 'warehouse_id') and line.warehouse_id:
#                     warehouse_id = line.warehouse_id.id
#                     break
#
#             # If not found in lines, try to get from purchase order
#             if not warehouse_id and invoice.invoice_origin:
#                 purchase_order = self.env['purchase.order'].search([
#                     ('name', '=', invoice.invoice_origin)
#                 ], limit=1)
#                 if purchase_order and purchase_order.picking_type_id:
#                     warehouse_id = purchase_order.picking_type_id.warehouse_id.id
#
#             # Get analytic account from invoice lines (first one found)
#             analytic_account_id = False
#             for line in invoice.invoice_line_ids:
#                 if line.analytic_distribution:
#                     # Get the first analytic account from distribution
#                     analytic_account_ids = [int(k) for k in line.analytic_distribution.keys()]
#                     if analytic_account_ids:
#                         analytic_account_id = analytic_account_ids[0]
#                         break
#
#             # Get purchase account from invoice lines (first product line)
#             purchase_account_id = False
#             for line in invoice.invoice_line_ids:
#                 if line.product_id and line.account_id:
#                     purchase_account_id = line.account_id.id
#                     break
#
#             report_obj.create({
#                 'invoice_date': invoice.invoice_date,
#                 'invoice_number': invoice.name,
#                 'vendor_id': invoice.partner_id.id,
#                 'analytic_account_id': analytic_account_id,
#                 'purchase_account_id': purchase_account_id,
#                 'warehouse_id': warehouse_id,
#                 'net_amount': invoice.amount_total,  # Changed from amount_untaxed to amount_total (includes tax)
#             })
#
#         # Return action to open list view
#         return {
#             'name': 'Purchase Vendor Report',
#             'type': 'ir.actions.act_window',
#             'res_model': 'purchase.vendor.report',
#             'view_mode': 'list',
#             'view_id': self.env.ref('purchase_vendor_report.view_purchase_vendor_report_list').id,
#             'target': 'current',
#             'domain': [],
#         }
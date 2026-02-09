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
            for line in invoice.invoice_line_ids:
                if line.product_id:  # Only lines with products
                    report_obj.create({
                        'invoice_date': invoice.invoice_date,
                        'invoice_number': invoice.name,
                        'buyer_id': invoice.buyer_id.id if invoice.buyer_id else False,
                        'vendor_id': invoice.partner_id.id,
                        'product_id': line.product_id.id,
                        'quantity': line.quantity,
                        'uom_id': line.product_uom_id.id,
                        'price_unit': line.price_unit,
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













# from odoo import models, fields, api
#
#
# class PurchaseBuyerReportWizard(models.TransientModel):
#     _name = 'purchase.buyer.report.wizard'
#     _description = 'Purchase Buyer Report Wizard'
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
#     buyer_ids = fields.Many2many(
#         'res.users',
#         string='Buyers',
#         required=True
#     )
#
#     def action_show_report(self):
#         """Open the report view with filtered data"""
#         self.ensure_one()
#
#         # Create the report records
#         report_obj = self.env['purchase.buyer.report']
#
#         # Clear existing report data first
#         report_obj.search([]).unlink()
#
#         # Search for purchase invoices with buyer_id matching criteria
#         domain = [
#             ('move_type', '=', 'in_invoice'),
#             ('state', '=', 'posted'),
#             ('invoice_date', '>=', self.date_from),
#             ('invoice_date', '<=', self.date_to),
#             ('buyer_id', 'in', self.buyer_ids.ids),  # Filter by buyer_id field in invoice
#         ]
#
#         invoices = self.env['account.move'].search(domain)
#
#         # Create report records from invoice lines
#         for invoice in invoices:
#             for line in invoice.invoice_line_ids:
#                 if line.product_id:  # Only lines with products
#                     report_obj.create({
#                         'invoice_date': invoice.invoice_date,
#                         'invoice_number': invoice.name,
#                         'buyer_id': invoice.buyer_id.id if invoice.buyer_id else False,
#                         'vendor_id': invoice.partner_id.id,
#                         'product_id': line.product_id.id,
#                         'quantity': line.quantity,
#                         'uom_id': line.product_uom_id.id,
#                         'price_unit': line.price_unit,
#                         'net_amount': line.price_total,  # Includes tax
#                     })
#
#         # Return action to open list view
#         return {
#             'name': 'Purchase Buyer Report',
#             'type': 'ir.actions.act_window',
#             'res_model': 'purchase.buyer.report',
#             'view_mode': 'list',
#             'view_id': self.env.ref('purchase_buyer_report.view_purchase_buyer_report_list').id,
#             'target': 'current',
#             'domain': [],
#         }
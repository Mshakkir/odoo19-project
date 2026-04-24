from odoo import models, fields, api
from odoo.exceptions import ValidationError


class PurchaseInvoiceReportWizard(models.TransientModel):
    _name = 'purchase.invoice.report.wizard'
    _description = 'Purchase Invoice Report Wizard'

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
    all_invoices = fields.Boolean(
        string='All Invoices',
        default=False
    )
    invoice_ids = fields.Many2many(
        'account.move',
        string='Invoice Numbers',
        domain=[('move_type', '=', 'in_invoice')]
    )
    invoice_status = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancel', 'Cancelled'),
        ('all', 'All')
    ], string='Invoice Status', default='all', required=True)

    @api.onchange('all_invoices')
    def _onchange_all_invoices(self):
        if self.all_invoices:
            self.invoice_ids = [(5, 0, 0)]

    def _get_currency_rate(self, invoice):
        """
        Return effective rate: how many company-currency units = 1 invoice-currency unit.
        Priority:
          1. invoice.manual_currency_rate  (from account_move customisation)
          2. res.currency.rate system rate
          3. Odoo built-in _get_rates()
        Returns 1.0 when invoice currency == company currency.
        """
        company_currency = invoice.company_id.currency_id
        invoice_currency = invoice.currency_id

        if not invoice_currency or invoice_currency == company_currency:
            return 1.0

        # 1. Manual rate stored on the invoice
        if hasattr(invoice, 'manual_currency_rate') and invoice.manual_currency_rate:
            return invoice.manual_currency_rate

        # 2. System rate table
        rate_date = invoice.invoice_date or invoice.date or fields.Date.today()
        rate_record = self.env['res.currency.rate'].search([
            ('currency_id', '=', invoice_currency.id),
            ('company_id', '=', invoice.company_id.id),
            ('name', '<=', str(rate_date)),
        ], order='name desc', limit=1)
        if rate_record and rate_record.inverse_company_rate:
            return rate_record.inverse_company_rate

        # 3. Odoo built-in fallback
        system_rate = invoice_currency._get_rates(invoice.company_id, rate_date)
        unit_per_company = system_rate.get(invoice_currency.id, 1.0)
        return (1.0 / unit_per_company) if unit_per_company else 1.0

    def action_show_report(self):
        self.ensure_one()

        if not self.all_invoices and not self.invoice_ids:
            raise ValidationError('Please select invoices or check "All Invoices"')

        report_obj = self.env['purchase.invoice.report']

        # Clear existing report data
        report_obj.search([]).unlink()

        # Build domain
        domain = [
            ('move_type', '=', 'in_invoice'),
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
        ]
        if not self.all_invoices:
            domain.append(('id', 'in', self.invoice_ids.ids))
        if self.invoice_status == 'draft':
            domain.append(('state', '=', 'draft'))
        elif self.invoice_status == 'posted':
            domain.append(('state', '=', 'posted'))
        elif self.invoice_status == 'cancel':
            domain.append(('state', '=', 'cancel'))

        invoices = self.env['account.move'].search(domain)

        # Cache rate per invoice to avoid repeated lookups
        rate_cache = {}

        for invoice in invoices:
            if invoice.id not in rate_cache:
                rate_cache[invoice.id] = self._get_currency_rate(invoice)
            rate = rate_cache[invoice.id]

            # Warehouse: from line first, then PO
            warehouse_id = False
            for line in invoice.invoice_line_ids:
                if hasattr(line, 'warehouse_id') and line.warehouse_id:
                    warehouse_id = line.warehouse_id.id
                    break
            if not warehouse_id and invoice.invoice_origin:
                purchase_order = self.env['purchase.order'].search([
                    ('name', '=', invoice.invoice_origin)
                ], limit=1)
                if purchase_order and purchase_order.picking_type_id:
                    warehouse_id = purchase_order.picking_type_id.warehouse_id.id

            for line in invoice.invoice_line_ids:
                if not line.product_id:
                    continue

                # Analytic account
                analytic_account_id = False
                if line.analytic_distribution:
                    analytic_ids = [int(k) for k in line.analytic_distribution.keys()]
                    if analytic_ids:
                        analytic_account_id = analytic_ids[0]

                buyer_id = invoice.buyer_id.id if hasattr(invoice, 'buyer_id') and invoice.buyer_id else False
                discount = line.discount_fixed if hasattr(line, 'discount_fixed') else 0.0

                # Convert all amounts to company currency using effective rate
                price_unit_cc     = line.price_unit * rate
                untaxed_amount_cc = line.price_subtotal * rate
                tax_value_cc      = (line.price_total - line.price_subtotal) * rate
                net_amount_cc     = line.price_total * rate

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
                    'price_unit': price_unit_cc,
                    'discount': discount,
                    'untaxed_amount': untaxed_amount_cc,
                    'tax_value': tax_value_cc,
                    'net_amount': net_amount_cc,
                })

        return {
            'name': 'Purchase Invoice Report',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.invoice.report',
            'view_mode': 'list',
            'view_id': self.env.ref('purchase_invoice_report.view_purchase_invoice_report_list').id,
            'target': 'current',
            'domain': [],
        }













# from odoo import models, fields, api
#
#
# class PurchaseInvoiceReportWizard(models.TransientModel):
#     _name = 'purchase.invoice.report.wizard'
#     _description = 'Purchase Invoice Report Wizard'
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
#     all_invoices = fields.Boolean(
#         string='All Invoices',
#         default=False
#     )
#     invoice_ids = fields.Many2many(
#         'account.move',
#         string='Invoice Numbers',
#         domain=[('move_type', '=', 'in_invoice')]
#     )
#     invoice_status = fields.Selection([
#         ('draft', 'Draft'),
#         ('posted', 'Posted'),
#         ('cancel', 'Cancelled'),
#         ('all', 'All')
#     ], string='Invoice Status', default='all', required=True)
#
#     @api.onchange('all_invoices')
#     def _onchange_all_invoices(self):
#         """When All Invoices is checked, clear invoice selection"""
#         if self.all_invoices:
#             self.invoice_ids = [(5, 0, 0)]
#
#     def action_show_report(self):
#         """Open the report view with filtered data"""
#         self.ensure_one()
#
#         # Validate: either all_invoices is checked OR invoices are selected
#         if not self.all_invoices and not self.invoice_ids:
#             raise models.ValidationError('Please select invoices or check "All Invoices"')
#
#         # Create the report records
#         report_obj = self.env['purchase.invoice.report']
#
#         # Clear existing report data first
#         report_obj.search([]).unlink()
#
#         # Search for purchase invoices matching criteria
#         domain = [
#             ('move_type', '=', 'in_invoice'),
#             ('invoice_date', '>=', self.date_from),
#             ('invoice_date', '<=', self.date_to),
#         ]
#
#         # Add invoice filter only if not "All Invoices"
#         if not self.all_invoices:
#             domain.append(('id', 'in', self.invoice_ids.ids))
#
#         # Add state filter based on selection
#         if self.invoice_status == 'draft':
#             domain.append(('state', '=', 'draft'))
#         elif self.invoice_status == 'posted':
#             domain.append(('state', '=', 'posted'))
#         elif self.invoice_status == 'cancel':
#             domain.append(('state', '=', 'cancel'))
#
#         invoices = self.env['account.move'].search(domain)
#
#         # Create report records from invoice lines
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
#             # Process each invoice line
#             for line in invoice.invoice_line_ids:
#                 if line.product_id:  # Only lines with products
#                     # Get analytic account from line
#                     analytic_account_id = False
#                     if line.analytic_distribution:
#                         analytic_account_ids = [int(k) for k in line.analytic_distribution.keys()]
#                         if analytic_account_ids:
#                             analytic_account_id = analytic_account_ids[0]
#
#                     # Get buyer from invoice
#                     buyer_id = invoice.buyer_id.id if invoice.buyer_id else False
#
#                     # Calculate discount (fixed) - discount_fixed field
#                     discount = line.discount_fixed if hasattr(line, 'discount_fixed') else 0.0
#
#                     # Calculate untaxed amount (subtotal) - price_subtotal field
#                     untaxed_amount = line.price_subtotal if hasattr(line, 'price_subtotal') else 0.0
#
#                     # Calculate tax value
#                     tax_value = line.tax_amount if hasattr(line, 'tax_amount') else 0.0
#
#                     report_obj.create({
#                         'invoice_date': invoice.invoice_date,
#                         'invoice_number': invoice.name,
#                         'analytic_account_id': analytic_account_id,
#                         'vendor_id': invoice.partner_id.id,
#                         'warehouse_id': warehouse_id,
#                         'product_id': line.product_id.id,
#                         'buyer_id': buyer_id,
#                         'quantity': line.quantity,
#                         'uom_id': line.product_uom_id.id,
#                         'price_unit': line.price_unit,
#                         'discount': discount,
#                         'untaxed_amount': untaxed_amount,
#                         'tax_value': tax_value,
#                         'net_amount': line.price_total,  # Includes tax
#                     })
#
#         # Return action to open list view
#         return {
#             'name': 'Purchase Invoice Report',
#             'type': 'ir.actions.act_window',
#             'res_model': 'purchase.invoice.report',
#             'view_mode': 'list',
#             'view_id': self.env.ref('purchase_invoice_report.view_purchase_invoice_report_list').id,
#             'target': 'current',
#             'domain': [],
#         }
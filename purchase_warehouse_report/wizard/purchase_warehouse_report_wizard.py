from odoo import models, fields, api
from odoo.exceptions import ValidationError


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
        if self.all_warehouses:
            self.warehouse_ids = [(5, 0, 0)]

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

        if not self.all_warehouses and not self.warehouse_ids:
            raise ValidationError('Please select warehouses or check "All Warehouses"')

        report_obj = self.env['purchase.warehouse.report']

        # Clear existing report data
        report_obj.search([]).unlink()

        # Build domain
        domain = [
            ('move_type', '=', 'in_invoice'),
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
        ]
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

            # Skip if no warehouse or not in selected warehouses
            if not warehouse_id:
                continue
            if not self.all_warehouses and warehouse_id not in self.warehouse_ids.ids:
                continue

            # Get effective currency rate for this invoice
            if invoice.id not in rate_cache:
                rate_cache[invoice.id] = self._get_currency_rate(invoice)
            rate = rate_cache[invoice.id]

            for line in invoice.invoice_line_ids:
                if not line.product_id:
                    continue

                # Analytic account
                analytic_id = False
                if line.analytic_distribution:
                    analytic_ids = [int(k) for k in line.analytic_distribution.keys()]
                    if analytic_ids:
                        analytic_id = analytic_ids[0]

                # Buyer from PO
                buyer_id = False
                if invoice.invoice_origin:
                    purchase_order = self.env['purchase.order'].search([
                        ('name', '=', invoice.invoice_origin)
                    ], limit=1)
                    if purchase_order and purchase_order.user_id:
                        buyer_id = purchase_order.user_id.id

                discount = line.discount_fixed if hasattr(line, 'discount_fixed') else 0.0

                # Convert all amounts to company currency using effective rate
                price_unit_cc     = line.price_unit * rate
                untaxed_amount_cc = line.price_subtotal * rate
                tax_value_cc      = (line.price_total - line.price_subtotal) * rate
                net_amount_cc     = line.price_total * rate

                report_obj.create({
                    'invoice_date': invoice.invoice_date,
                    'invoice_number': invoice.name,
                    'vendor_id': invoice.partner_id.id,
                    'warehouse_id': warehouse_id,
                    'buyer_id': buyer_id,
                    'product_id': line.product_id.id,
                    'quantity': line.quantity,
                    'uom_id': line.product_uom_id.id,
                    'price_unit': price_unit_cc,
                    'discount': discount,
                    'untaxed_amount': untaxed_amount_cc,
                    'tax_value': tax_value_cc,
                    'net_amount': net_amount_cc,
                    'analytic_account_id': analytic_id,
                })

        return {
            'name': 'Purchase Warehouse Report',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.warehouse.report',
            'view_mode': 'list',
            'view_id': self.env.ref('purchase_warehouse_report.view_purchase_warehouse_report_list').id,
            'target': 'current',
            'domain': [],
        }


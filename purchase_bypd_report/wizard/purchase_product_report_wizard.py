from odoo import models, fields, api
from odoo.exceptions import ValidationError


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
        if self.all_products:
            self.product_ids = [(5, 0, 0)]

    def _get_currency_rate(self, invoice):
        """
        Return effective rate: how many company-currency units = 1 invoice-currency unit.
        Priority:
          1. invoice.manual_currency_rate  (from your account_move customisation)
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

        if not self.all_products and not self.product_ids:
            raise ValidationError('Please select products or check "All Products"')

        report_obj = self.env['purchase.bypd.report']
        company_currency = self.env.company.currency_id

        # Build domain
        domain = [
            ('move_id.move_type', '=', 'in_invoice'),
            ('move_id.invoice_date', '>=', self.date_from),
            ('move_id.invoice_date', '<=', self.date_to),
        ]
        if not self.all_products:
            domain.append(('product_id', 'in', self.product_ids.ids))
        if self.invoice_status == 'draft':
            domain.append(('move_id.state', '=', 'draft'))
        elif self.invoice_status == 'posted':
            domain.append(('move_id.state', '=', 'posted'))
        elif self.invoice_status == 'cancel':
            domain.append(('move_id.state', '=', 'cancel'))

        invoice_lines = self.env['account.move.line'].search(domain)

        # Clear existing report data
        report_obj.search([]).unlink()

        # Cache rate per invoice to avoid repeated lookups
        rate_cache = {}

        for line in invoice_lines:
            if not line.product_id:
                continue

            invoice = line.move_id

            if invoice.id not in rate_cache:
                rate_cache[invoice.id] = self._get_currency_rate(invoice)
            rate = rate_cache[invoice.id]

            # Convert all amounts to company currency
            price_unit_cc     = line.price_unit * rate
            price_subtotal_cc = line.price_subtotal * rate
            tax_amount_cc     = (line.price_total - line.price_subtotal) * rate
            price_total_cc    = line.price_total * rate

            # Analytic account
            analytic_account_id = False
            if line.analytic_distribution:
                analytic_ids = list(line.analytic_distribution.keys())
                if analytic_ids:
                    analytic_account_id = int(analytic_ids[0])

            # Warehouse
            warehouse_id = line.warehouse_id.id if line.warehouse_id else False

            # Buyer from PO
            buyer_id = False
            if invoice.invoice_origin:
                purchase_order = self.env['purchase.order'].search([
                    ('name', '=', invoice.invoice_origin)
                ], limit=1)
                if purchase_order:
                    buyer_id = purchase_order.user_id.id

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
                # All amount fields stored in company currency
                'price_unit': price_unit_cc,
                'price_total': price_total_cc,
                'discount_fixed': line.discount_fixed if hasattr(line, 'discount_fixed') else 0,
                'price_subtotal': price_subtotal_cc,
                'tax_amount': tax_amount_cc,
            })

        return {
            'name': 'Purchase Product Report',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.bypd.report',
            'view_mode': 'list',
            'view_id': self.env.ref('purchase_bypd_report.view_purchase_bypd_report_list').id,
            'target': 'current',
            'domain': [],
        }

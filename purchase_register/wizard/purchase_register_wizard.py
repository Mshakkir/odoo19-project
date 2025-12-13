from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import base64
import io
import logging

_logger = logging.getLogger(__name__)

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter


class PurchaseRegisterWizard(models.TransientModel):
    _name = 'purchase.register.wizard'
    _description = 'Purchase Register Report Wizard'

    date_from = fields.Date(
        string='From Date',
        required=True,
        default=fields.Date.context_today
    )
    date_to = fields.Date(
        string='To Date',
        required=True,
        default=fields.Date.context_today
    )
    partner_ids = fields.Many2many(
        'res.partner',
        string='Suppliers',
        domain=[('supplier_rank', '>', 0)],
        help='Leave empty to include all suppliers'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    report_type = fields.Selection([
        ('summary', 'Summary Report'),
        ('detailed', 'Detailed Report'),
    ], string='Report Type', default='summary', required=True)

    group_by = fields.Selection([
        ('supplier', 'Group by Supplier'),
        ('date', 'Group by Date'),
        ('none', 'No Grouping'),
    ], string='Group By', default='supplier')

    data_source = fields.Selection([
        ('purchase_order', 'Purchase Orders Only'),
        ('invoice', 'Invoices Only'),
        ('both', 'Both PO and Invoices'),
    ], string='Data Source', default='both', required=True)

    date_filter = fields.Selection([
        ('custom', 'Custom'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ], string='Date Filter', default='custom', required=True)

    @api.onchange('date_filter')
    def _onchange_date_filter(self):
        """Auto-calculate date range based on filter selection"""
        today = fields.Date.context_today(self)

        if self.date_filter == 'daily':
            self.date_from = today
            self.date_to = today
        elif self.date_filter == 'weekly':
            # Start of week (Monday)
            start = today - timedelta(days=today.weekday())
            self.date_from = start
            self.date_to = start + timedelta(days=6)
        elif self.date_filter == 'monthly':
            # Start of month
            self.date_from = today.replace(day=1)
            # End of month
            if today.month == 12:
                next_month = today.replace(year=today.year + 1, month=1, day=1)
            else:
                next_month = today.replace(month=today.month + 1, day=1)
            self.date_to = next_month - timedelta(days=1)
        elif self.date_filter == 'yearly':
            # Start of year
            self.date_from = today.replace(month=1, day=1)
            # End of year
            self.date_to = today.replace(month=12, day=31)
        # For 'custom', don't change the dates

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_from > record.date_to:
                raise UserError(_('From Date must be before To Date'))

    def _get_purchase_order_data(self):
        """Fetch purchase order data"""
        domain = [
            ('date_order', '>=', self.date_from),
            ('date_order', '<=', self.date_to),
            ('state', 'in', ['purchase', 'done']),
            ('company_id', '=', self.company_id.id),
        ]

        if self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))

        purchase_orders = self.env['purchase.order'].search(domain, order='date_order, partner_id')

        po_data = []
        for po in purchase_orders:
            # Get related invoices for payment calculation
            invoices = self.env['account.move'].search([
                ('invoice_origin', '=', po.name),
                ('move_type', '=', 'in_invoice'),
                ('state', '=', 'posted')
            ])

            # Calculate total paid for all related invoices
            total_invoice_amount = 0
            total_paid = 0

            for inv in invoices:
                total_invoice_amount += inv.amount_total

                # Method 1: Try payment_state and residual
                if hasattr(inv, 'payment_state') and inv.payment_state == 'paid':
                    total_paid += inv.amount_total
                elif hasattr(inv, 'amount_residual'):
                    total_paid += (inv.amount_total - inv.amount_residual)
                else:
                    # Method 2: Search for matching payments (Odoo Mates compatible)
                    from datetime import timedelta
                    payments = self.env['account.payment'].search([
                        ('partner_id', '=', po.partner_id.id),
                        ('payment_type', '=', 'outbound'),
                        ('state', '=', 'posted'),
                        ('date', '>=', inv.invoice_date - timedelta(days=30)),
                        ('date', '<=', inv.invoice_date + timedelta(days=30)),
                    ])

                    for payment in payments:
                        # Match by amount or reference
                        if abs(payment.amount - inv.amount_total) < 0.01:
                            total_paid += payment.amount
                        elif hasattr(payment, 'ref') and payment.ref and inv.name in payment.ref:
                            total_paid += payment.amount
                        elif hasattr(payment, 'memo') and payment.memo and inv.name in str(payment.memo):
                            total_paid += payment.amount

            for line in po.order_line:
                # Get warehouse from analytic account
                warehouse_name = ''
                if hasattr(line, 'account_analytic_id') and line.account_analytic_id:
                    warehouse_name = line.account_analytic_id.name

                # Get taxes - handle different field names across Odoo versions
                taxes = False
                if hasattr(line, 'tax_id'):
                    taxes = line.tax_id
                elif hasattr(line, 'taxes_id'):
                    taxes = line.taxes_id

                # Calculate tax amount
                tax_amount = 0
                if taxes:
                    tax_amount = sum(line.price_subtotal * (tax.amount / 100) for tax in taxes)

                # Calculate Trade Discount (line discount)
                trade_discount = 0
                if hasattr(line, 'discount') and line.discount > 0:
                    trade_discount = (line.product_qty * line.price_unit * line.discount) / 100

                # Additional Discount (from PO level discount if exists)
                addin_discount = 0
                if hasattr(po, 'additional_discount') and po.additional_discount:
                    if po.amount_untaxed > 0:
                        addin_discount = (line.price_subtotal / po.amount_untaxed) * po.additional_discount

                # Additional Cost (from PO level additional costs like freight)
                addin_cost = 0
                if hasattr(po, 'additional_cost') and po.additional_cost:
                    if po.amount_untaxed > 0:
                        addin_cost = (line.price_subtotal / po.amount_untaxed) * po.additional_cost

                # Round Off (calculated at document level, distributed proportionally)
                round_off = 0
                if hasattr(po, 'amount_round') and po.amount_round:
                    if po.amount_untaxed > 0:
                        round_off = (line.price_subtotal / po.amount_untaxed) * po.amount_round

                # Convert datetime to date if needed
                order_date = po.date_order
                if hasattr(order_date, 'date'):
                    order_date = order_date.date()

                # Calculate line total
                line_total = line.price_total

                # Calculate proportional paid and balance for this line
                paid_amount = 0
                balance_amount = line_total

                if total_invoice_amount > 0:
                    line_proportion = line_total / po.amount_total if po.amount_total > 0 else 0
                    paid_amount = total_paid * line_proportion
                    balance_amount = line_total - paid_amount

                po_data.append({
                    'date': order_date,
                    'document_number': po.name or '',
                    'document_type': 'Purchase Order',
                    'supplier_name': po.partner_id.name,
                    'supplier_vat': po.partner_id.vat or '',
                    'warehouse': warehouse_name,
                    'product': line.product_id.name or line.name,
                    'quantity': line.product_qty,
                    'unit_price': line.price_unit,
                    'subtotal': line.price_subtotal,
                    'trade_discount': trade_discount,
                    'addin_discount': addin_discount,
                    'addin_cost': addin_cost,
                    'tax_amount': tax_amount,
                    'round_off': round_off,
                    'total': line_total,
                    'paid': paid_amount,
                    'balance': balance_amount,
                    'taxes': ', '.join(taxes.mapped('name')) if taxes else '',
                    'currency': po.currency_id.name,
                })

        return po_data

    def _get_invoice_data(self):
        """Fetch invoice data (if accounting module exists)"""
        invoice_data = []

        # Check if account.move model exists
        if 'account.move' not in self.env:
            return invoice_data

        try:
            domain = [
                ('invoice_date', '>=', self.date_from),
                ('invoice_date', '<=', self.date_to),
                ('move_type', '=', 'in_invoice'),
                ('state', '=', 'posted'),
                ('company_id', '=', self.company_id.id),
            ]

            if self.partner_ids:
                domain.append(('partner_id', 'in', self.partner_ids.ids))

            invoices = self.env['account.move'].search(domain, order='invoice_date, partner_id')

            for invoice in invoices:
                # Calculate paid amount for the invoice
                invoice_paid = 0

                # Method 1: Check if invoice has payment_state and amount fields
                if hasattr(invoice, 'payment_state'):
                    if invoice.payment_state in ['paid', 'in_payment', 'partial']:
                        invoice_paid = invoice.amount_total - invoice.amount_residual

                # Method 2: If still 0, check reconciled payment items
                if invoice_paid == 0:
                    for line in invoice.line_ids.filtered(lambda l: l.account_id.account_type == 'liability_payable'):
                        for partial in line.matched_debit_ids:
                            invoice_paid += partial.amount
                        for partial in line.matched_credit_ids:
                            invoice_paid += partial.amount

                # Method 3: If still 0, search for related payments by partner and amount
                if invoice_paid == 0:
                    payments = self.env['account.payment'].search([
                        ('partner_id', '=', invoice.partner_id.id),
                        ('payment_type', '=', 'outbound'),
                        ('state', '=', 'posted'),
                        ('date', '>=', invoice.invoice_date),
                    ])

                    for payment in payments:
                        if hasattr(payment, 'reconciled_bill_ids') and invoice in payment.reconciled_bill_ids:
                            invoice_paid += payment.amount
                        elif hasattr(payment, 'reconciled_invoice_ids') and invoice in payment.reconciled_invoice_ids:
                            invoice_paid += payment.amount

                # Ensure we don't exceed the total
                if invoice_paid > invoice.amount_total:
                    invoice_paid = invoice.amount_total

                for line in invoice.invoice_line_ids:
                    # Skip section and note lines
                    if line.display_type in ['line_section', 'line_note']:
                        continue

                    # Get warehouse from analytic account/distribution
                    warehouse_name = ''
                    if hasattr(line, 'analytic_distribution') and line.analytic_distribution:
                        analytic_ids = [int(k) for k in line.analytic_distribution.keys()]
                        if analytic_ids:
                            analytic_account = self.env['account.analytic.account'].browse(analytic_ids[0])
                            if analytic_account:
                                warehouse_name = analytic_account.name
                    elif hasattr(line, 'analytic_account_id') and line.analytic_account_id:
                        warehouse_name = line.analytic_account_id.name

                    taxes = line.tax_ids

                    # Calculate tax amount
                    tax_amount = 0
                    if taxes:
                        tax_amount = sum(line.price_subtotal * (tax.amount / 100) for tax in taxes)

                    # Calculate Trade Discount (line discount)
                    trade_discount = 0
                    if hasattr(line, 'discount') and line.discount > 0:
                        trade_discount = (line.quantity * line.price_unit * line.discount) / 100

                    # Additional Discount (invoice level)
                    addin_discount = 0
                    if hasattr(invoice, 'additional_discount') and invoice.additional_discount:
                        if invoice.amount_untaxed > 0:
                            addin_discount = (
                                                     line.price_subtotal / invoice.amount_untaxed) * invoice.additional_discount

                    # Additional Cost (invoice level freight/charges)
                    addin_cost = 0
                    if hasattr(invoice, 'additional_cost') and invoice.additional_cost:
                        if invoice.amount_untaxed > 0:
                            addin_cost = (line.price_subtotal / invoice.amount_untaxed) * invoice.additional_cost

                    # Round Off (proportional distribution)
                    round_off = 0
                    if hasattr(invoice, 'amount_round') and invoice.amount_round:
                        if invoice.amount_untaxed > 0:
                            round_off = (line.price_subtotal / invoice.amount_untaxed) * invoice.amount_round

                    # Calculate line total
                    line_total = line.price_total

                    # Calculate proportional paid and balance for this line
                    line_paid = 0
                    line_balance = line_total

                    if invoice.amount_total > 0:
                        line_proportion = line_total / invoice.amount_total
                        line_paid = invoice_paid * line_proportion
                        line_balance = line_total - line_paid

                    invoice_data.append({
                        'date': invoice.invoice_date,
                        'document_number': invoice.name or '',
                        'document_type': 'Vendor Bill',
                        'supplier_name': invoice.partner_id.name,
                        'supplier_vat': invoice.partner_id.vat or '',
                        'warehouse': warehouse_name,
                        'product': line.product_id.name or line.name,
                        'quantity': line.quantity,
                        'unit_price': line.price_unit,
                        'subtotal': line.price_subtotal,
                        'trade_discount': trade_discount,
                        'addin_discount': addin_discount,
                        'addin_cost': addin_cost,
                        'tax_amount': tax_amount,
                        'round_off': round_off,
                        'total': line_total,
                        'paid': line_paid,
                        'balance': line_balance,
                        'taxes': ', '.join(taxes.mapped('name')) if taxes else '',
                        'currency': invoice.currency_id.name,
                    })
        except Exception as e:
            # If there's any error accessing invoices, just return empty list
            pass

        return invoice_data

    def _get_purchase_data(self):
        """Fetch purchase data based on selected source"""
        purchase_data = []

        if self.data_source in ['purchase_order', 'both']:
            purchase_data.extend(self._get_purchase_order_data())

        if self.data_source in ['invoice', 'both']:
            purchase_data.extend(self._get_invoice_data())

        # Sort by date
        purchase_data.sort(key=lambda x: x['date'])

        return purchase_data

    def _get_detailed_data(self):
        """Get data grouped by document for detailed report"""
        purchase_data = self._get_purchase_data()

        # Group by document
        documents = {}
        for line in purchase_data:
            doc_key = line['document_number']
            if doc_key not in documents:
                documents[doc_key] = {
                    'date': line['date'],
                    'document_number': line['document_number'],
                    'document_type': line['document_type'],
                    'supplier_name': line['supplier_name'],
                    'supplier_vat': line['supplier_vat'],
                    'warehouse': line['warehouse'],
                    'lines': [],
                    'total': 0,
                    'tax_amount': 0,
                    'net_amount': 0,
                }

            documents[doc_key]['lines'].append(line)
            documents[doc_key]['total'] += line['total']
            documents[doc_key]['tax_amount'] += line['tax_amount']

        # Convert to list and sort
        detailed_data = list(documents.values())
        detailed_data.sort(key=lambda x: x['date'])

        return detailed_data

    def action_show_details(self):
        """Show purchase register details in tree view"""
        self.ensure_one()
        purchase_data = self._get_purchase_data()

        if not purchase_data:
            raise UserError(_('No purchase data found for the selected period.'))

        # Create temporary records in the line model
        PurchaseLine = self.env['purchase.register.line']

        # Delete old records to keep database clean
        old_lines = PurchaseLine.search([])
        old_lines.unlink()

        # Create new records
        line_ids = []
        for data in purchase_data:
            line = PurchaseLine.create({
                'date': data['date'],
                'document_type': data['document_type'],
                'document_number': data['document_number'],
                'supplier_name': data['supplier_name'],
                'supplier_vat': data['supplier_vat'],
                'warehouse': data['warehouse'],
                'product': data['product'],
                'quantity': data['quantity'],
                'unit_price': data['unit_price'],
                'subtotal': data['subtotal'],
                'trade_discount': data['trade_discount'],
                'addin_discount': data['addin_discount'],
                'addin_cost': data['addin_cost'],
                'taxes': data['taxes'],
                'tax_amount': data['tax_amount'],
                'round_off': data['round_off'],
                'total': data['total'],
                'paid': data['paid'],
                'balance': data['balance'],
                'currency': data['currency'],
            })
            line_ids.append(line.id)

        # Return tree view action
        return {
            'name': _('Purchase Register Details'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.register.line',
            'view_mode': 'tree',
            'domain': [('id', 'in', line_ids)],
            'context': {
                'create': False,
                'edit': False,
                'delete': False,
            },
            'target': 'current',
        }

    def action_print_pdf(self):
        """Generate PDF Report"""
        self.ensure_one()
        purchase_data = self._get_purchase_data()

        if not purchase_data:
            raise UserError(_('No purchase data found for the selected period.'))

        # Return the report action with self (wizard) as the record
        return self.env.ref('purchase_register.action_report_purchase_register').report_action(self)

    def action_export_excel(self):
        """Generate Excel Report"""
        self.ensure_one()
        purchase_data = self._get_purchase_data()

        if not purchase_data:
            raise UserError(_('No purchase data found for the selected period.'))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Purchase Register')

        # Formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4472C4',
            'font_color': 'white',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })

        title_format = workbook.add_format({
            'bold': True,
            'font_size': 16,
            'align': 'center',
            'valign': 'vcenter'
        })

        date_format = workbook.add_format({'num_format': 'dd/mm/yyyy'})
        currency_format = workbook.add_format({'num_format': '#,##0.00'})

        # Title
        worksheet.merge_range('A1:T1', 'PURCHASE REGISTER', title_format)
        worksheet.merge_range('A2:T2', f'{self.company_id.name}', title_format)
        worksheet.merge_range('A3:T3',
                              f'Period: {self.date_from.strftime("%d/%m/%Y")} to {self.date_to.strftime("%d/%m/%Y")}',
                              title_format)

        # Headers
        headers = [
            'Date', 'Document Type', 'Document No.', 'Supplier Name', 'Supplier VAT/GST',
            'Warehouse', 'Product/Service', 'Quantity', 'Unit Price', 'Subtotal',
            'Trade Dis', 'AddIn Dis', 'AddIn Cost', 'Tax', 'Tax Amount', 'Round Off',
            'Total', 'Paid', 'Balance', 'Currency'
        ]

        for col, header in enumerate(headers):
            worksheet.write(4, col, header, header_format)

        # Data
        row = 5
        total_subtotal = 0
        total_trade_dis = 0
        total_addin_dis = 0
        total_addin_cost = 0
        total_tax = 0
        total_round_off = 0
        total_amount = 0
        total_paid = 0
        total_balance = 0

        for record in purchase_data:
            worksheet.write_datetime(row, 0, record['date'], date_format)
            worksheet.write(row, 1, record['document_type'])
            worksheet.write(row, 2, record['document_number'])
            worksheet.write(row, 3, record['supplier_name'])
            worksheet.write(row, 4, record['supplier_vat'])
            worksheet.write(row, 5, record['warehouse'])
            worksheet.write(row, 6, record['product'])
            worksheet.write(row, 7, record['quantity'])
            worksheet.write(row, 8, record['unit_price'], currency_format)
            worksheet.write(row, 9, record['subtotal'], currency_format)
            worksheet.write(row, 10, record.get('trade_discount', 0), currency_format)
            worksheet.write(row, 11, record.get('addin_discount', 0), currency_format)
            worksheet.write(row, 12, record.get('addin_cost', 0), currency_format)
            worksheet.write(row, 13, record['taxes'])
            worksheet.write(row, 14, record['tax_amount'], currency_format)
            worksheet.write(row, 15, record.get('round_off', 0), currency_format)
            worksheet.write(row, 16, record['total'], currency_format)
            worksheet.write(row, 17, record['paid'], currency_format)
            worksheet.write(row, 18, record['balance'], currency_format)
            worksheet.write(row, 19, record['currency'])

            total_subtotal += record['subtotal']
            total_trade_dis += record.get('trade_discount', 0)
            total_addin_dis += record.get('addin_discount', 0)
            total_addin_cost += record.get('addin_cost', 0)
            total_tax += record['tax_amount']
            total_round_off += record.get('round_off', 0)
            total_amount += record['total']
            total_paid += record['paid']
            total_balance += record['balance']
            row += 1

        # Totals
        total_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D9E1F2',
            'border': 1,
            'num_format': '#,##0.00'
        })

        worksheet.write(row, 8, 'TOTAL:', total_format)
        worksheet.write(row, 9, total_subtotal, total_format)
        worksheet.write(row, 10, total_trade_dis, total_format)
        worksheet.write(row, 11, total_addin_dis, total_format)
        worksheet.write(row, 12, total_addin_cost, total_format)
        worksheet.write(row, 14, total_tax, total_format)
        worksheet.write(row, 15, total_round_off, total_format)
        worksheet.write(row, 16, total_amount, total_format)
        worksheet.write(row, 17, total_paid, total_format)
        worksheet.write(row, 18, total_balance, total_format)

        # Column widths
        worksheet.set_column('A:A', 12)
        worksheet.set_column('B:B', 15)
        worksheet.set_column('C:C', 15)
        worksheet.set_column('D:D', 25)
        worksheet.set_column('E:E', 18)
        worksheet.set_column('F:F', 20)
        worksheet.set_column('G:G', 30)
        worksheet.set_column('H:H', 10)
        worksheet.set_column('I:S', 12)
        worksheet.set_column('T:T', 10)

        workbook.close()
        output.seek(0)

        attachment = self.env['ir.attachment'].create({
            'name': f'Purchase_Register_{self.date_from}_{self.date_to}.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(output.read()),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }


class PurchaseRegisterLine(models.TransientModel):
    """Temporary model to display purchase register lines in tree view"""
    _name = 'purchase.register.line'
    _description = 'Purchase Register Line'
    _order = 'date desc, id desc'

    date = fields.Date(string='Date')
    document_type = fields.Char(string='Type')
    document_number = fields.Char(string='Document No.')
    supplier_name = fields.Char(string='Supplier')
    supplier_vat = fields.Char(string='VAT')
    warehouse = fields.Char(string='Warehouse')
    product = fields.Char(string='Product')
    quantity = fields.Float(string='Qty', digits=(16, 2))
    unit_price = fields.Float(string='Unit Price', digits=(16, 2))
    subtotal = fields.Float(string='Subtotal', digits=(16, 2))
    trade_discount = fields.Float(string='Trade Dis', digits=(16, 2))
    addin_discount = fields.Float(string='AddIn Dis', digits=(16, 2))
    addin_cost = fields.Float(string='AddIn Cost', digits=(16, 2))
    taxes = fields.Char(string='Tax')
    tax_amount = fields.Float(string='Tax Amt', digits=(16, 2))
    round_off = fields.Float(string='Round Off', digits=(16, 2))
    total = fields.Float(string='Total', digits=(16, 2))
    paid = fields.Float(string='Paid', digits=(16, 2))
    balance = fields.Float(string='Balance', digits=(16, 2))
    currency = fields.Char(string='Currency')
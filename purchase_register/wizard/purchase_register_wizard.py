from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime
import base64
import io

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
    ], string='Report Type', default='detailed', required=True)

    group_by = fields.Selection([
        ('supplier', 'Group by Supplier'),
        ('date', 'Group by Date'),
        ('none', 'No Grouping'),
    ], string='Group By', default='supplier')

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_from > record.date_to:
                raise UserError(_('From Date must be before To Date'))

    def _get_purchase_data(self):
        """Fetch purchase order and invoice data"""
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

        purchase_data = []
        for invoice in invoices:
            for line in invoice.invoice_line_ids:
                taxes = line.tax_ids
                tax_amount = sum(line.price_subtotal * (tax.amount / 100) for tax in taxes)

                purchase_data.append({
                    'date': invoice.invoice_date,
                    'invoice_number': invoice.name or '',
                    'supplier_name': invoice.partner_id.name,
                    'supplier_vat': invoice.partner_id.vat or '',
                    'product': line.product_id.name or line.name,
                    'quantity': line.quantity,
                    'unit_price': line.price_unit,
                    'subtotal': line.price_subtotal,
                    'tax_amount': tax_amount,
                    'total': line.price_total,
                    'taxes': ', '.join(taxes.mapped('name')),
                    'currency': invoice.currency_id.name,
                })

        return purchase_data

    def action_print_pdf(self):
        """Generate PDF Report"""
        self.ensure_one()
        purchase_data = self._get_purchase_data()

        if not purchase_data:
            raise UserError(_('No purchase data found for the selected period.'))

        data = {
            'wizard_id': self.id,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'company_name': self.company_id.name,
            'report_type': self.report_type,
            'group_by': self.group_by,
            'purchase_data': purchase_data,
        }

        return self.env.ref('purchase_register.action_report_purchase_register').report_action(self, data=data)

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
        worksheet.merge_range('A1:L1', 'PURCHASE REGISTER', title_format)
        worksheet.merge_range('A2:L2', f'{self.company_id.name}', title_format)
        worksheet.merge_range('A3:L3',
                              f'Period: {self.date_from.strftime("%d/%m/%Y")} to {self.date_to.strftime("%d/%m/%Y")}',
                              title_format)

        # Headers
        headers = [
            'Date', 'Invoice No.', 'Supplier Name', 'Supplier VAT/GST',
            'Product/Service', 'Quantity', 'Unit Price', 'Subtotal',
            'Tax', 'Tax Amount', 'Total', 'Currency'
        ]

        for col, header in enumerate(headers):
            worksheet.write(4, col, header, header_format)

        # Data
        row = 5
        total_subtotal = 0
        total_tax = 0
        total_amount = 0

        for record in purchase_data:
            worksheet.write_datetime(row, 0, record['date'], date_format)
            worksheet.write(row, 1, record['invoice_number'])
            worksheet.write(row, 2, record['supplier_name'])
            worksheet.write(row, 3, record['supplier_vat'])
            worksheet.write(row, 4, record['product'])
            worksheet.write(row, 5, record['quantity'])
            worksheet.write(row, 6, record['unit_price'], currency_format)
            worksheet.write(row, 7, record['subtotal'], currency_format)
            worksheet.write(row, 8, record['taxes'])
            worksheet.write(row, 9, record['tax_amount'], currency_format)
            worksheet.write(row, 10, record['total'], currency_format)
            worksheet.write(row, 11, record['currency'])

            total_subtotal += record['subtotal']
            total_tax += record['tax_amount']
            total_amount += record['total']
            row += 1

        # Totals
        total_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D9E1F2',
            'border': 1,
            'num_format': '#,##0.00'
        })

        worksheet.write(row, 6, 'TOTAL:', total_format)
        worksheet.write(row, 7, total_subtotal, total_format)
        worksheet.write(row, 9, total_tax, total_format)
        worksheet.write(row, 10, total_amount, total_format)

        # Column widths
        worksheet.set_column('A:A', 12)
        worksheet.set_column('B:B', 15)
        worksheet.set_column('C:C', 25)
        worksheet.set_column('D:D', 18)
        worksheet.set_column('E:E', 30)
        worksheet.set_column('F:F', 10)
        worksheet.set_column('G:K', 12)
        worksheet.set_column('L:L', 10)

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
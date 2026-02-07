from odoo import models, fields, api


class ReportBySalespersonWizard(models.TransientModel):
    _name = 'report.by.salesperson.wizard'
    _description = 'Report by Salesperson Wizard'

    date_from = fields.Date(string='Date From', required=True)
    date_to = fields.Date(string='Date To', required=True)
    salesperson_ids = fields.Many2many('res.users', string='Salespersons')

    def action_generate_report(self):
        """Generate and display the report"""
        return self.env.ref('sales_invoice_reports.action_salesperson_report_display').report_action(self)

    def _get_report_values(self):
        """Prepare data for the report template"""
        self.ensure_one()

        # Build domain for invoices
        domain = [
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('state', '=', 'posted')
        ]

        # Filter by salesperson if selected
        if self.salesperson_ids:
            domain.append(('invoice_user_id', 'in', self.salesperson_ids.ids))

        # Fetch invoices
        invoices = self.env['account.move'].search(domain, order='invoice_user_id, invoice_date')

        # Group data by salesperson
        salesperson_data = []
        grouped_invoices = {}

        for invoice in invoices:
            salesperson = invoice.invoice_user_id
            if not salesperson:
                salesperson_name = 'No Salesperson'
                salesperson_id = 0
            else:
                salesperson_name = salesperson.name
                salesperson_id = salesperson.id

            if salesperson_id not in grouped_invoices:
                grouped_invoices[salesperson_id] = {
                    'salesperson_name': salesperson_name,
                    'invoices': [],
                    'total': 0.0
                }

            # Prepare invoice lines
            lines = []
            sequence = 1
            for line in invoice.invoice_line_ids:
                lines.append({
                    'sequence': sequence,
                    'code': line.product_id.default_code or '',
                    'name': line.name or line.product_id.name or '',
                    'quantity': line.quantity,
                    'uom': line.product_uom_id.name or '',
                    'price_unit': line.price_unit,
                    'discount': line.discount,
                    'subtotal': line.price_subtotal
                })
                sequence += 1

            # Get account code (sales account)
            account_code = ''
            if invoice.invoice_line_ids:
                account_code = invoice.invoice_line_ids[0].account_id.code or ''

            # Add invoice data
            invoice_data = {
                'date': invoice.invoice_date.strftime('%d/%m/%Y') if invoice.invoice_date else '',
                'number': invoice.name or '',
                'customer': invoice.partner_id.name or '',
                'account': account_code,
                'lines': lines,
                'total': invoice.amount_total
            }

            grouped_invoices[salesperson_id]['invoices'].append(invoice_data)
            grouped_invoices[salesperson_id]['total'] += invoice.amount_total

        # Convert to list
        for sp_id, sp_info in grouped_invoices.items():
            salesperson_data.append(sp_info)

        return {
            'salesperson_data': salesperson_data,
            'title': 'Sales Invoice Report',
            'date_from': self.date_from.strftime('%d/%m/%Y') if self.date_from else '',
            'date_to': self.date_to.strftime('%d/%m/%Y') if self.date_to else '',
        }


class SalespersonReport(models.AbstractModel):
    _name = 'report.sales_invoice_reports.salesperson_report_display_template'
    _description = 'Salesperson Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Override to pass custom data to the report template"""
        docs = self.env['report.by.salesperson.wizard'].browse(docids)

        if not docs:
            return {}

        # Get data from the wizard
        wizard = docs[0]
        report_data = wizard._get_report_values()

        return {
            'doc_ids': docids,
            'doc_model': 'report.by.salesperson.wizard',
            'docs': docs,
            'salesperson_data': report_data['salesperson_data'],
            'title': report_data['title'],
            'date_from': report_data['date_from'],
            'date_to': report_data['date_to'],
        }
# -*- coding: utf-8 -*-

from odoo import models, api


class SalesReportBySalesperson(models.AbstractModel):
    _name = 'report.sales_invoice_reports.report_sales_by_salesperson'
    _description = 'Sales Report by Salesperson'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Prepare data for the report"""

        date_from = data.get('date_from')
        date_to = data.get('date_to')
        salesperson_ids = data.get('salesperson_ids', [])

        # Build domain
        domain = [
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('state', '=', 'posted'),
        ]

        if date_from:
            domain.append(('invoice_date', '>=', date_from))
        if date_to:
            domain.append(('invoice_date', '<=', date_to))
        if salesperson_ids:
            domain.append(('invoice_user_id', 'in', salesperson_ids))

        # Get invoices
        invoices = self.env['account.move'].search(domain, order='invoice_user_id, invoice_date, name')

        # Group by salesperson
        salesperson_data = {}
        for invoice in invoices:
            salesperson = invoice.invoice_user_id
            if not salesperson:
                continue

            if salesperson.id not in salesperson_data:
                salesperson_data[salesperson.id] = {
                    'salesperson': salesperson,
                    'invoices': [],
                    'total': 0.0
                }

            invoice_lines = []
            invoice_total = 0.0

            for line in invoice.invoice_line_ids:
                if line.display_type in ['line_section', 'line_note']:
                    continue

                line_total = line.price_subtotal if invoice.move_type == 'out_invoice' else -line.price_subtotal
                invoice_total += line_total

                invoice_lines.append({
                    'sequence': line.sequence,
                    'code': line.product_id.default_code or '',
                    'name': line.name or line.product_id.name,
                    'quantity': line.quantity,
                    'uom': line.product_uom_id.name,
                    'price_unit': line.price_unit,
                    'discount': line.discount,
                    'subtotal': line_total,
                })

            salesperson_data[salesperson.id]['invoices'].append({
                'date': invoice.invoice_date,
                'number': invoice.name,
                'customer': invoice.partner_id.name,
                'account': invoice.invoice_line_ids[0].account_id.code if invoice.invoice_line_ids else '',
                'lines': invoice_lines,
                'total': invoice_total,
            })

            salesperson_data[salesperson.id]['total'] += invoice_total

        return {
            'doc_ids': docids,
            'doc_model': 'account.move',
            'docs': invoices,
            'date_from': date_from,
            'date_to': date_to,
            'salesperson_data': salesperson_data,
            'company': self.env.company,
        }
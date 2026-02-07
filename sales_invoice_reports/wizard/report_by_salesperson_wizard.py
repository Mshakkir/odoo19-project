# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ReportBySalespersonWizard(models.TransientModel):
    _name = 'report.by.salesperson.wizard'
    _description = 'Report by Salesperson Wizard'

    show_all_salespersons = fields.Boolean(string='All Salespersons', default=False)
    user_id = fields.Many2one('res.users', string='Salesperson')
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To', default=fields.Date.today)
    invoice_state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancel', 'Cancelled'),
        ('all', 'All')
    ], string='Invoice Status', default='all')

    @api.onchange('show_all_salespersons')
    def _onchange_show_all_salespersons(self):
        """Clear salesperson selection when showing all salespersons"""
        if self.show_all_salespersons:
            self.user_id = False

    def action_apply(self):
        """Apply filter and show salesperson report"""
        self.ensure_one()

        # Build domain for the report model
        domain = []

        # Only filter by salesperson if not showing all
        if not self.show_all_salespersons:
            if not self.user_id:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Warning',
                        'message': 'Please select a salesperson or check "All Salespersons"',
                        'type': 'warning',
                        'sticky': False,
                    }
                }
            domain.append(('user_id', '=', self.user_id.id))

        # Only filter by state if not 'all'
        if self.invoice_state and self.invoice_state != 'all':
            domain.append(('invoice_state', '=', self.invoice_state))

        # Only add date filters if they are set
        if self.date_from:
            domain.append(('invoice_date', '>=', self.date_from))
        if self.date_to:
            domain.append(('invoice_date', '<=', self.date_to))

        # Set report name
        if self.show_all_salespersons:
            report_name = 'Sales Report - All Salespersons'
        else:
            report_name = f'Sales Report - {self.user_id.display_name}'

        return {
            'name': report_name,
            'type': 'ir.actions.act_window',
            'res_model': 'salesperson.invoice.report',
            'view_mode': 'list,pivot,graph',
            'domain': domain,
            'context': {'search_default_posted': 1},
            'target': 'current',
        }

    def action_show_report(self):
        """Show formatted report view"""
        self.ensure_one()

        # Build domain for invoices
        domain = [
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('state', '=', 'posted'),
        ]

        if self.date_from:
            domain.append(('invoice_date', '>=', self.date_from))
        if self.date_to:
            domain.append(('invoice_date', '<=', self.date_to))

        # Filter by salesperson
        if not self.show_all_salespersons:
            if not self.user_id:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Warning',
                        'message': 'Please select a salesperson or check "All Salespersons"',
                        'type': 'warning',
                        'sticky': False,
                    }
                }
            domain.append(('invoice_user_id', '=', self.user_id.id))

        # Get invoices
        invoices = self.env['account.move'].search(domain, order='invoice_user_id, invoice_date, name')

        # Clear previous report data
        self.env['salesperson.report.display'].search([]).unlink()

        # Prepare report data
        report_lines = []
        line_sequence = 0

        for invoice in invoices:
            for line in invoice.invoice_line_ids:
                if line.display_type in ['line_section', 'line_note']:
                    continue

                line_total = line.price_subtotal if invoice.move_type == 'out_invoice' else -line.price_subtotal

                line_sequence += 1
                report_lines.append({
                    'sequence': line_sequence,
                    'salesperson_id': invoice.invoice_user_id.id,
                    'salesperson_name': invoice.invoice_user_id.name,
                    'invoice_date': invoice.invoice_date,
                    'invoice_number': invoice.name,
                    'customer_name': invoice.partner_id.name,
                    'account_code': line.account_id.code if line.account_id else '',
                    'product_code': line.product_id.default_code or '',
                    'product_name': line.name or line.product_id.name,
                    'quantity': line.quantity,
                    'uom': line.product_uom_id.name,
                    'price_unit': line.price_unit,
                    'discount': line.discount,
                    'price_subtotal': line_total,
                    'invoice_id': invoice.id,
                    'is_invoice_line': True,
                })

        # Create report records
        self.env['salesperson.report.display'].create(report_lines)

        # Set report title
        if self.show_all_salespersons:
            report_title = 'Sales Invoice Report - All Salespersons'
        else:
            report_title = f'Sales Invoice Report - {self.user_id.name}'

        if self.date_from and self.date_to:
            report_title += f' ({self.date_from} to {self.date_to})'

        return {
            'name': report_title,
            'type': 'ir.actions.act_window',
            'res_model': 'salesperson.report.display',
            'view_mode': 'list',
            'view_id': self.env.ref('sales_invoice_reports.view_salesperson_report_display_list').id,
            'target': 'current',
            'context': {
                'group_by': ['salesperson_name', 'invoice_number'],
            }
        }
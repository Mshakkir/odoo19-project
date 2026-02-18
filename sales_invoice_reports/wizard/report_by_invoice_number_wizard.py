# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ReportByInvoiceNumberWizard(models.TransientModel):
    _name = 'report.by.invoice.number.wizard'
    _description = 'Report by Invoice Number Wizard'

    show_all_invoices = fields.Boolean(string='All Invoices', default=False)
    invoice_ids = fields.Many2many('account.move', string='Invoices',
                                   domain="[('move_type', 'in', ['out_invoice', 'out_refund'])]")
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To', default=fields.Date.today)
    invoice_state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancel', 'Cancelled'),
        ('all', 'All')
    ], string='Invoice Status', default='all')

    @api.onchange('show_all_invoices')
    def _onchange_show_all_invoices(self):
        """Clear invoice selection when showing all"""
        if self.show_all_invoices:
            self.invoice_ids = [(5, 0, 0)]

    def action_apply(self):
        """Apply filter and show invoice report"""
        self.ensure_one()

        # Build domain for the report model
        domain = []

        # Only filter by invoice if not showing all
        if not self.show_all_invoices:
            if not self.invoice_ids:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Warning',
                        'message': 'Please select at least one invoice or check "All Invoices"',
                        'type': 'warning',
                        'sticky': False,
                    }
                }
            domain.append(('invoice_id', 'in', self.invoice_ids.ids))

        # Only filter by state if not 'all'
        if self.invoice_state and self.invoice_state != 'all':
            domain.append(('invoice_state', '=', self.invoice_state))

        # Only add date filters if they are set
        if self.date_from:
            domain.append(('invoice_date', '>=', self.date_from))
        if self.date_to:
            domain.append(('invoice_date', '<=', self.date_to))

        # Set report name
        if self.show_all_invoices:
            report_name = 'Sales Report - All Invoices'
        elif len(self.invoice_ids) == 1:
            report_name = f'Sales Report - {self.invoice_ids[0].name}'
        else:
            report_name = f'Sales Report - {len(self.invoice_ids)} Invoices'

        return {
            'name': report_name,
            'type': 'ir.actions.act_window',
            'res_model': 'invoice.number.report',
            'view_mode': 'list,pivot,graph',
            'domain': domain,
            'context': {'search_default_posted': 1},
            'target': 'current',
        }
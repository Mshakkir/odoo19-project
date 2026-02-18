# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ReportByCustomerWizard(models.TransientModel):
    _name = 'report.by.customer.wizard'
    _description = 'Report by Customer Wizard'

    show_all_customers = fields.Boolean(string='All Customers', default=False)
    partner_id = fields.Many2many('res.partner', string='Customer')
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To', default=fields.Date.today)
    invoice_state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancel', 'Cancelled'),
        ('all', 'All')
    ], string='Invoice Status', default='all')

    @api.onchange('show_all_customers')
    def _onchange_show_all_customers(self):
        """Clear customer selection when showing all customers"""
        if self.show_all_customers:
            self.partner_ids = [(5,0,0)]

    def action_apply(self):
        """Apply filter and show customer report"""
        self.ensure_one()

        # Build domain for the report model
        domain = []

        # Only filter by customer if not showing all
        if not self.show_all_customers:
            if not self.partner_id:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Warning',
                        'message': 'Please select a customer or check "All Customers"',
                        'type': 'warning',
                        'sticky': False,
                    }
                }
            domain.append(('partner_id', 'in', self.partner_ids.ids))

        # Only filter by state if not 'all'
        if self.invoice_state and self.invoice_state != 'all':
            domain.append(('invoice_state', '=', self.invoice_state))

        # Only add date filters if they are set
        if self.date_from:
            domain.append(('invoice_date', '>=', self.date_from))
        if self.date_to:
            domain.append(('invoice_date', '<=', self.date_to))

        # Set report name
        if self.show_all_customers:
            report_name = 'Sales Report - All Customers'
        else:
            report_name = f'Sales Report - {self.partner_id.display_name}'

        return {
            'name': report_name,
            'type': 'ir.actions.act_window',
            'res_model': 'customer.invoice.report',
            'view_mode': 'list,pivot,graph',
            'domain': domain,
            'context': {'search_default_posted': 1},
            'target': 'current',
        }
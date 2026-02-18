# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ReportByProductWizard(models.TransientModel):
    _name = 'report.by.product.wizard'
    _description = 'Report by Product Wizard'

    show_all_products = fields.Boolean(string='All Products', default=False)
    product_ids = fields.Many2many('product.product', string='Products')
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To', default=fields.Date.today)
    invoice_state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancel', 'Cancelled'),
        ('all', 'All')
    ], string='Invoice Status', default='all')

    @api.onchange('show_all_products')
    def _onchange_show_all_products(self):
        """Clear product selection when showing all products"""
        if self.show_all_products:
            self.product_ids = [(5, 0, 0)]

    def action_apply(self):
        """Apply filter and show product report"""
        self.ensure_one()

        # Build domain for the report model
        domain = []

        # Only filter by product if not showing all
        if not self.show_all_products:
            if not self.product_ids:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Warning',
                        'message': 'Please select at least one product or check "All Products"',
                        'type': 'warning',
                        'sticky': False,
                    }
                }
            domain.append(('product_id', 'in', self.product_ids.ids))

        # Only filter by state if not 'all'
        if self.invoice_state and self.invoice_state != 'all':
            domain.append(('invoice_state', '=', self.invoice_state))

        # Only add date filters if they are set
        if self.date_from:
            domain.append(('invoice_date', '>=', self.date_from))
        if self.date_to:
            domain.append(('invoice_date', '<=', self.date_to))

        # Set report name
        if self.show_all_products:
            report_name = 'Sales Report - All Products'
        elif len(self.product_ids) == 1:
            report_name = f'Sales Report - {self.product_ids[0].display_name}'
        else:
            report_name = f'Sales Report - {len(self.product_ids)} Products'

        return {
            'name': report_name,
            'type': 'ir.actions.act_window',
            'res_model': 'product.invoice.report',
            'view_mode': 'list,pivot,graph',
            'domain': domain,
            'context': {'search_default_posted': 1},
            'target': 'current',
        }
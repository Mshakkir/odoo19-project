# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ReportByProductCategoryWizard(models.TransientModel):
    _name = 'report.by.product.category.wizard'
    _description = 'Report by Product Category Wizard'

    show_all_categories = fields.Boolean(string='All Categories', default=False)
    categ_ids = fields.Many2many('product.category', string='Product Category')
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To', default=fields.Date.today)
    invoice_state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancel', 'Cancelled'),
        ('all', 'All')
    ], string='Invoice Status', default='all')

    @api.onchange('show_all_categories')
    def _onchange_show_all_categories(self):
        """Clear category selection when showing all categories"""
        if self.show_all_categories:
            self.categ_ids = [(5,0,0)]

    def action_apply(self):
        """Apply filter and show product category report"""
        self.ensure_one()

        # Build domain for the report model
        domain = []

        # Only filter by category if not showing all
        if not self.show_all_categories:
            if not self.categ_id:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Warning',
                        'message': 'Please select a product category or check "All Categories"',
                        'type': 'warning',
                        'sticky': False,
                    }
                }
            domain.append(('categ_id', 'in', self.categ_ids.ids))

        # Only filter by state if not 'all'
        if self.invoice_state and self.invoice_state != 'all':
            domain.append(('invoice_state', '=', self.invoice_state))

        # Only add date filters if they are set
        if self.date_from:
            domain.append(('invoice_date', '>=', self.date_from))
        if self.date_to:
            domain.append(('invoice_date', '<=', self.date_to))

        # Set report name
        if self.show_all_categories:
            report_name = 'Sales Report - All Product Categories'
        else:
            report_name = f'Sales Report - {self.categ_id.display_name}'

        return {
            'name': report_name,
            'type': 'ir.actions.act_window',
            'res_model': 'product.category.invoice.report',
            'view_mode': 'list,pivot,graph',
            'domain': domain,
            'context': {'search_default_posted': 1},
            'target': 'current',
        }
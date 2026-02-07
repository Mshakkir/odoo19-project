# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ReportByProductWizard(models.TransientModel):
    _name = 'report.by.product.wizard'
    _description = 'Report by Product Wizard'

    product_id = fields.Many2one('product.product', string='Product', required=True)
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To', default=fields.Date.today)
    invoice_state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancel', 'Cancelled'),
        ('all', 'All')
    ], string='Invoice Status', default='posted')

    def action_apply(self):
        """Apply filter and show product report"""
        self.ensure_one()

        # Build domain for the report model (not account.move)
        domain = [('product_id', '=', self.product_id.id)]

        if self.invoice_state != 'all':
            domain.append(('invoice_state', '=', self.invoice_state))
        else:
            domain.append(('invoice_state', '!=', 'cancel'))

        if self.date_from:
            domain.append(('invoice_date', '>=', self.date_from))
        if self.date_to:
            domain.append(('invoice_date', '<=', self.date_to))

        # Create context with filters
        context = {
            'search_default_product_id': self.product_id.id,
            'default_product_id': self.product_id.id,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'invoice_state': self.invoice_state,
        }

        return {
            'name': f'Sales Report - {self.product_id.display_name}',
            'type': 'ir.actions.act_window',
            'res_model': 'product.invoice.report',
            'view_mode': 'list,pivot,graph',  # Changed from 'tree' to 'list'
            'domain': domain,
            'context': context,
            'target': 'current',
        }
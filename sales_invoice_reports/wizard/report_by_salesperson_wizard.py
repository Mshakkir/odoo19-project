# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ReportBySalespersonWizard(models.TransientModel):
    _name = 'report.by.salesperson.wizard'
    _description = 'Report by Salesperson Wizard'

    user_id = fields.Many2one('res.users', string='Salesperson', required=True)
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To', default=fields.Date.today)
    invoice_state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancel', 'Cancelled'),
        ('all', 'All')
    ], string='Invoice Status', default='all')

    def action_apply(self):
        """Apply filter and show salesperson report"""
        self.ensure_one()

        # Build domain for the report model
        domain = [('user_id', '=', self.user_id.id)]

        # Only filter by state if not 'all'
        if self.invoice_state and self.invoice_state != 'all':
            domain.append(('invoice_state', '=', self.invoice_state))

        # Only add date filters if they are set
        if self.date_from:
            domain.append(('invoice_date', '>=', self.date_from))
        if self.date_to:
            domain.append(('invoice_date', '<=', self.date_to))

        return {
            'name': f'Sales Report - {self.user_id.display_name}',
            'type': 'ir.actions.act_window',
            'res_model': 'salesperson.invoice.report',
            'view_mode': 'list,pivot,graph',
            'domain': domain,
            'context': {'search_default_user_id': self.user_id.id},
            'target': 'current',
        }
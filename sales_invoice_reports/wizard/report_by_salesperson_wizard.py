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
    ], string='Invoice Status', default='posted')

    def action_apply(self):
        """Apply filter and show salesperson report"""
        self.ensure_one()

        # Build domain for filtering
        domain = [
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('invoice_user_id', '=', self.user_id.id),
        ]

        if self.invoice_state != 'all':
            domain.append(('state', '=', self.invoice_state))
        else:
            domain.append(('state', '!=', 'cancel'))

        if self.date_from:
            domain.append(('invoice_date', '>=', self.date_from))
        if self.date_to:
            domain.append(('invoice_date', '<=', self.date_to))

        # Create context with filters
        context = {
            'search_default_user_id': self.user_id.id,
            'default_user_id': self.user_id.id,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'invoice_state': self.invoice_state,
        }

        return {
            'name': f'Sales Report - {self.user_id.display_name}',
            'type': 'ir.actions.act_window',
            'res_model': 'salesperson.invoice.report',
            'view_mode': 'tree,pivot,graph',
            'domain': domain,
            'context': context,
            'target': 'current',
        }
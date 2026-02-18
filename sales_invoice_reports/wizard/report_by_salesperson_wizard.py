# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ReportBySalespersonWizard(models.TransientModel):
    _name = 'report.by.salesperson.wizard'
    _description = 'Report by Salesperson Wizard'

    show_all_salespersons = fields.Boolean(string='All Salespersons', default=False)
    user_ids = fields.Many2many('res.users', string='Salesperson')
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
            self.user_ids = [(5,0,0)]

    def action_apply(self):
        """Apply filter and show salesperson report"""
        self.ensure_one()

        # Build domain for the report model
        domain = []

        # Only filter by salesperson if not showing all
        if not self.show_all_salespersons:
            if not self.user_ids:
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
            domain.append(('user_id', 'in', self.user_ids.ids))

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
        elif len(self.user_ids) == 1:
            report_name = f'Sales Report - {self.user_ids[0].display_name}'
        else:
            report_name = f'Sales Report - {len(self.user_ids)} Salespersons'

        return {
            'name': report_name,
            'type': 'ir.actions.act_window',
            'res_model': 'salesperson.invoice.report',
            'view_mode': 'list,pivot,graph',
            'domain': domain,
            'context': {'search_default_posted': 1},
            'target': 'current',
        }
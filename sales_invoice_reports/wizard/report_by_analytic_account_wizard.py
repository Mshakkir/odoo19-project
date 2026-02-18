# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ReportByAnalyticAccountWizard(models.TransientModel):
    _name = 'report.by.analytic.account.wizard'
    _description = 'Report by Analytic Account Wizard'

    show_all_analytic_accounts = fields.Boolean(string='All warehouse', default=False)
    analytic_account_ids = fields.Many2many('account.analytic.account', string='Warehouses')
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To', default=fields.Date.today)
    invoice_state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancel', 'Cancelled'),
        ('all', 'All')
    ], string='Invoice Status', default='all')

    @api.onchange('show_all_analytic_accounts')
    def _onchange_show_all_analytic_accounts(self):
        """Clear analytic account selection when showing all"""
        if self.show_all_analytic_accounts:
            self.analytic_account_ids = [(5, 0, 0)]

    def action_apply(self):
        """Apply filter and show analytic account report"""
        self.ensure_one()

        # Build domain for the report model
        domain = []

        # Only filter by analytic account if not showing all
        if not self.show_all_analytic_accounts:
            if not self.analytic_account_ids:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Warning',
                        'message': 'Please select at least one analytic account or check "All Analytic Accounts"',
                        'type': 'warning',
                        'sticky': False,
                    }
                }
            domain.append(('analytic_account_id', 'in', self.analytic_account_ids.ids))

        # Only filter by state if not 'all'
        if self.invoice_state and self.invoice_state != 'all':
            domain.append(('invoice_state', '=', self.invoice_state))

        # Only add date filters if they are set
        if self.date_from:
            domain.append(('invoice_date', '>=', self.date_from))
        if self.date_to:
            domain.append(('invoice_date', '<=', self.date_to))

        # Set report name
        if self.show_all_analytic_accounts:
            report_name = 'Sales Report - All Analytic Accounts'
        elif len(self.analytic_account_ids) == 1:
            report_name = f'Sales Report - {self.analytic_account_ids[0].display_name}'
        else:
            report_name = f'Sales Report - {len(self.analytic_account_ids)} Analytic Accounts'

        return {
            'name': report_name,
            'type': 'ir.actions.act_window',
            'res_model': 'analytic.account.invoice.report',
            'view_mode': 'list,pivot,graph',
            'domain': domain,
            'context': {'search_default_posted': 1},
            'target': 'current',
        }
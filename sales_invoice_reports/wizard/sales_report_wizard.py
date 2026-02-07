# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SalesReportWizard(models.TransientModel):
    _name = 'sales.report.wizard'
    _description = 'Sales Report Wizard'

    date_from = fields.Date(string='Date From', required=True)
    date_to = fields.Date(string='Date To', required=True, default=fields.Date.today)
    salesperson_ids = fields.Many2many('res.users', string='Salespersons')

    def action_print_report(self):
        """Generate PDF report"""
        self.ensure_one()

        data = {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'salesperson_ids': self.salesperson_ids.ids if self.salesperson_ids else [],
        }

        return self.env.ref('sales_invoice_reports.action_report_sales_by_salesperson').report_action(self, data=data)
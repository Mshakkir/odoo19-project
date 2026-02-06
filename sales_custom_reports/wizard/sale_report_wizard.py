# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class SaleReportWizard(models.TransientModel):
    _name = 'sale.report.wizard'
    _description = 'Sale Invoice Report Wizard'

    report_type = fields.Selection([
        ('product', 'Product'),
        ('category', 'Product Category'),
        ('partner', 'Partner'),
        ('warehouse', 'Warehouse'),
        ('salesman', 'Salesman'),
    ], string='Report Type', required=True)

    product_id = fields.Many2one('product.product', string='Product')
    category_id = fields.Many2one('product.category', string='Product Category')
    partner_id = fields.Many2one('res.partner', string='Partner')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    salesman_id = fields.Many2one('res.users', string='Salesman', domain=[('share', '=', False)])

    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')

    @api.onchange('report_type')
    def _onchange_report_type(self):
        """Clear other fields when report type changes"""
        self.product_id = False
        self.category_id = False
        self.partner_id = False
        self.warehouse_id = False
        self.salesman_id = False

    def action_generate_report(self):
        """Generate the sales invoice report based on selected criteria"""
        self.ensure_one()

        # Validate that the appropriate field is filled
        if self.report_type == 'product' and not self.product_id:
            raise UserError('Please select a product.')
        elif self.report_type == 'category' and not self.category_id:
            raise UserError('Please select a product category.')
        elif self.report_type == 'partner' and not self.partner_id:
            raise UserError('Please select a partner.')
        elif self.report_type == 'warehouse' and not self.warehouse_id:
            raise UserError('Please select a warehouse.')
        elif self.report_type == 'salesman' and not self.salesman_id:
            raise UserError('Please select a salesman.')

        # Get the record ID based on report type
        record_id = False
        if self.report_type == 'product':
            record_id = self.product_id.id
        elif self.report_type == 'category':
            record_id = self.category_id.id
        elif self.report_type == 'partner':
            record_id = self.partner_id.id
        elif self.report_type == 'warehouse':
            record_id = self.warehouse_id.id
        elif self.report_type == 'salesman':
            record_id = self.salesman_id.id

        # Get sales invoice data
        invoices = self.env['account.move'].get_sales_report_data(
            self.report_type,
            record_id,
            self.date_from,
            self.date_to
        )

        if not invoices:
            raise UserError('No sales invoices found for the selected criteria.')

        # Prepare data for the report
        data = {
            'report_type': self.report_type,
            'record_id': record_id,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'invoice_ids': invoices.ids,
        }

        # Return action to open tree view with the filtered invoices
        return {
            'name': self._get_report_title(),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', invoices.ids)],
            'context': {
                'default_move_type': 'out_invoice',
                'search_default_group_by_partner': 1 if self.report_type != 'partner' else 0,
            },
            'target': 'current',
        }

    def action_print_report(self):
        """Print PDF report"""
        self.ensure_one()

        # Validate fields same as generate_report
        if self.report_type == 'product' and not self.product_id:
            raise UserError('Please select a product.')
        elif self.report_type == 'category' and not self.category_id:
            raise UserError('Please select a product category.')
        elif self.report_type == 'partner' and not self.partner_id:
            raise UserError('Please select a partner.')
        elif self.report_type == 'warehouse' and not self.warehouse_id:
            raise UserError('Please select a warehouse.')
        elif self.report_type == 'salesman' and not self.salesman_id:
            raise UserError('Please select a salesman.')

        # Get the record ID
        record_id = False
        if self.report_type == 'product':
            record_id = self.product_id.id
        elif self.report_type == 'category':
            record_id = self.category_id.id
        elif self.report_type == 'partner':
            record_id = self.partner_id.id
        elif self.report_type == 'warehouse':
            record_id = self.warehouse_id.id
        elif self.report_type == 'salesman':
            record_id = self.salesman_id.id

        # Get sales invoice data
        invoices = self.env['account.move'].get_sales_report_data(
            self.report_type,
            record_id,
            self.date_from,
            self.date_to
        )

        if not invoices:
            raise UserError('No sales invoices found for the selected criteria.')

        # Prepare report data
        data = {
            'wizard_id': self.id,
            'invoice_ids': invoices.ids,
        }

        return self.env.ref('sales_custom_reports.action_report_sales_custom').report_action(self, data=data)

    def _get_report_title(self):
        """Get report title based on report type and selected record"""
        if self.report_type == 'product':
            return f'Sales Invoice Report - {self.product_id.name}'
        elif self.report_type == 'category':
            return f'Sales Invoice Report - {self.category_id.name}'
        elif self.report_type == 'partner':
            return f'Sales Invoice Report - {self.partner_id.name}'
        elif self.report_type == 'warehouse':
            return f'Sales Invoice Report - {self.warehouse_id.name}'
        elif self.report_type == 'salesman':
            return f'Sales Invoice Report - {self.salesman_id.name}'
        return 'Sales Invoice Report'
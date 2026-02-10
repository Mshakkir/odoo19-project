# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class ProductProfitMarginWizard(models.TransientModel):
    _name = 'product.profit.margin.wizard'
    _description = 'Product Profit Margin Report Wizard'

    product_filter = fields.Selection([
        ('all', 'All'),
        ('by_group', 'By Group'),
        ('by_product', 'By Product')
    ], string='Product', default='all', required=True)

    bill_mode = fields.Selection([
        ('all', 'All'),
        ('billed', 'Billed'),
        ('unbilled', 'Unbilled')
    ], string='Bill Mode', default='all', required=True)

    date_from = fields.Date(string='From', required=True, default=fields.Date.today)
    date_to = fields.Date(string='To', required=True, default=fields.Date.today)

    group_id = fields.Many2one('product.category', string='Group')
    product_id = fields.Many2one('product.product', string='Product')

    def action_show_report(self):
        """Generate and show the profit margin report based on SALES INVOICES"""
        self.ensure_one()

        if self.date_from > self.date_to:
            raise UserError('From date cannot be greater than To date!')

        _logger.info(f"Searching for invoices between {self.date_from} and {self.date_to}")

        # Clear old report data
        old_reports = self.env['product.profit.margin.report'].search([])
        old_reports.unlink()

        # Build domain for filtering INVOICE LINES
        domain = [
            ('move_id.invoice_date', '>=', self.date_from),
            ('move_id.invoice_date', '<=', self.date_to),
            ('move_id.move_type', '=', 'out_invoice'),
            ('move_id.state', '=', 'posted'),
            ('product_id', '!=', False),
            ('display_type', 'in', [False, 'product']),
        ]

        # Apply product filter
        if self.product_filter == 'by_group' and self.group_id:
            domain.append(('product_id.categ_id', '=', self.group_id.id))
        elif self.product_filter == 'by_product' and self.product_id:
            domain.append(('product_id', '=', self.product_id.id))

        # Get invoice lines
        invoice_lines = self.env['account.move.line'].search(domain)

        _logger.info(f"Found {len(invoice_lines)} invoice lines matching criteria")

        if not invoice_lines:
            raise UserError(
                f'No customer invoices found between {self.date_from} and {self.date_to}.\n\n'
                'Please check:\n'
                '1. You have posted Customer Invoices in this date range\n'
                '2. The invoices have line items with products'
            )

        # Prepare report data
        report_data = []
        product_data = {}

        for line in invoice_lines:
            product = line.product_id
            if not product:
                continue

            key = product.id

            if key not in product_data:
                product_data[key] = {
                    'product_id': product.id,
                    'product_name': product.name,
                    'product_code': product.default_code or '',
                    'category': product.categ_id.name if product.categ_id else '',
                    'date': line.move_id.invoice_date,
                    'order_ref': line.move_id.name,
                    'qty': 0.0,
                    'uom': product.uom_id.name if product.uom_id else '',
                    'rate': 0.0,
                    'total': 0.0,
                    'unit_cost': product.standard_price,
                    'total_cost': 0.0,
                    'profit': 0.0,
                    'profit_margin': 0.0,
                }

            # Accumulate quantities and amounts
            product_data[key]['qty'] += line.quantity
            product_data[key]['total'] += line.price_subtotal
            product_data[key]['total_cost'] += (product.standard_price * line.quantity)

        # Calculate rate, profit and margin after accumulation
        for key in product_data:
            # Calculate average rate (total / qty)
            if product_data[key]['qty'] > 0:
                product_data[key]['rate'] = product_data[key]['total'] / product_data[key]['qty']
            else:
                product_data[key]['rate'] = 0.0

            # Calculate profit
            product_data[key]['profit'] = product_data[key]['total'] - product_data[key]['total_cost']

            # Calculate profit margin percentage
            if product_data[key]['total'] > 0:
                product_data[key]['profit_margin'] = ((product_data[key]['total'] - product_data[key]['total_cost']) /
                                                      product_data[key]['total']) * 100
            else:
                product_data[key]['profit_margin'] = 0.0

        # Create report records
        for data in product_data.values():
            report_line = self.env['product.profit.margin.report'].create(data)
            report_data.append(report_line.id)

        _logger.info(f"Created {len(report_data)} report records")

        return {
            'name': f'Sales Product Profit Report ({len(report_data)} products)',
            'type': 'ir.actions.act_window',
            'res_model': 'product.profit.margin.report',
            'view_mode': 'list',
            'domain': [('id', 'in', report_data)],
            'target': 'current',
            'context': {
                'report_title': f'Sales Product Profit Report - {self.date_from} to {self.date_to}'
            }
        }
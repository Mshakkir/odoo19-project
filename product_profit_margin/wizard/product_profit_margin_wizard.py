# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import timedelta


class ProductProfitMarginWizard(models.TransientModel):
    _name = 'product.profit.margin.wizard'
    _description = 'Product Profit Margin Report Wizard'

    report_type = fields.Selection([
        ('short', 'Short'),
        ('detailed', 'Detailed'),
        ('monthly', 'Monthly')
    ], string='Type', default='short', required=True)

    form_type = fields.Selection([
        ('normal', 'Normal Mode'),
        ('detailed', 'Detailed Mode')
    ], string='Form Type', default='normal', required=True)

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

    filter_type = fields.Selection([
        ('today', 'Today'),
        ('one_week', 'One Week'),
        ('two_week', 'Two Week'),
        ('one_month', 'One Month'),
        ('two_month', 'Two Month'),
        ('quarterly', 'Quarterly'),
        ('six_month', 'Six Month'),
        ('one_year', 'One Year'),
        ('financial', 'Financial'),
        ('custom', 'Custom')
    ], string='Filter', default='one_month', required=True)

    date_from = fields.Date(string='From', required=True, default=fields.Date.today)
    date_to = fields.Date(string='To', required=True, default=fields.Date.today)

    group_id = fields.Many2one('product.category', string='Group')
    product_id = fields.Many2one('product.product', string='Product')

    use_master_rate = fields.Boolean(string='Use Master Rate', default=False)

    @api.onchange('filter_type')
    def _onchange_filter_type(self):
        """Update date range based on filter type"""
        today = fields.Date.today()

        if self.filter_type == 'today':
            self.date_from = today
            self.date_to = today
        elif self.filter_type == 'one_week':
            self.date_from = today - timedelta(days=7)
            self.date_to = today
        elif self.filter_type == 'two_week':
            self.date_from = today - timedelta(days=14)
            self.date_to = today
        elif self.filter_type == 'one_month':
            self.date_from = today - timedelta(days=30)
            self.date_to = today
        elif self.filter_type == 'two_month':
            self.date_from = today - timedelta(days=60)
            self.date_to = today
        elif self.filter_type == 'quarterly':
            self.date_from = today - timedelta(days=90)
            self.date_to = today
        elif self.filter_type == 'six_month':
            self.date_from = today - timedelta(days=180)
            self.date_to = today
        elif self.filter_type == 'one_year':
            self.date_from = today - timedelta(days=365)
            self.date_to = today

    def action_show_report(self):
        """
        Generate and show the profit margin report based on SALES INVOICES

        DATA SOURCES:
        - Sales Data: From account.move.line (Posted customer invoices)
        - Selling Price: line.price_unit (from invoice line)
        - Total Sales: line.price_subtotal (unit price × quantity)
        - Product Cost: product.standard_price (cost set in product form)
        - Total Cost: product.standard_price × quantity
        - Profit: Total Sales - Total Cost
        - Profit Margin %: (Profit / Total Sales) × 100
        """
        self.ensure_one()

        if self.date_from > self.date_to:
            raise UserError('From date cannot be greater than To date!')

        # Clear old report data
        old_reports = self.env['product.profit.margin.report'].search([])
        old_reports.unlink()

        # Build domain for filtering INVOICE LINES
        # We use account.move.line for invoice lines
        domain = [
            ('move_id.invoice_date', '>=', self.date_from),
            ('move_id.invoice_date', '<=', self.date_to),
            ('move_id.move_type', '=', 'out_invoice'),  # Customer invoices only
            ('move_id.state', '=', 'posted'),  # Posted invoices only
            ('product_id', '!=', False),  # Must have a product
            ('display_type', '=', False),  # Exclude section/note lines
        ]

        # Apply product filter
        if self.product_filter == 'by_group' and self.group_id:
            domain.append(('product_id.categ_id', '=', self.group_id.id))
        elif self.product_filter == 'by_product' and self.product_id:
            domain.append(('product_id', '=', self.product_id.id))

        # Get invoice lines
        invoice_lines = self.env['account.move.line'].search(domain)

        if not invoice_lines:
            # Provide helpful error message
            all_lines = self.env['account.move.line'].search([
                ('move_id.invoice_date', '>=', self.date_from),
                ('move_id.invoice_date', '<=', self.date_to),
                ('move_id.move_type', '=', 'out_invoice'),
                ('product_id', '!=', False),
            ])

            if not all_lines:
                raise UserError(
                    f'No customer invoices found between {self.date_from} and {self.date_to}.\n\n'
                    'Please check:\n'
                    '1. You have created Customer Invoices in this date range\n'
                    '2. The invoices have line items with products\n\n'
                    'Go to: Invoicing > Customers > Invoices'
                )
            else:
                states = all_lines.mapped('move_id.state')
                raise UserError(
                    f'No POSTED invoices found between {self.date_from} and {self.date_to}.\n\n'
                    f'Found {len(all_lines)} invoice lines, but their states are: {", ".join(set(states))}\n\n'
                    'Please post your invoices (click "Confirm" button on the invoice).'
                )

        # Prepare report data
        report_data = []
        product_data = {}

        for line in invoice_lines:
            product = line.product_id
            if not product:
                continue

            # Use product ID as key to aggregate same products
            key = product.id

            if key not in product_data:
                product_data[key] = {
                    'product_id': product.id,
                    'product_name': product.name,
                    'product_code': product.default_code or '',
                    'category': product.categ_id.name if product.categ_id else '',
                    'date': line.move_id.invoice_date,
                    'order_ref': line.move_id.name,  # Invoice number
                    'qty': 0.0,
                    'uom': product.uom_id.name if product.uom_id else '',
                    'rate': 0.0,
                    'total': 0.0,
                    'unit_cost': product.standard_price,  # Product cost from inventory
                    'total_cost': 0.0,
                    'profit': 0.0,
                    'profit_margin': 0.0,
                }

            # Accumulate quantities and amounts
            product_data[key]['qty'] += line.quantity
            product_data[key]['total'] += line.price_subtotal  # Total sales amount (excluding tax)
            product_data[key]['rate'] = line.price_unit  # Selling price per unit
            product_data[key]['total_cost'] += (product.standard_price * line.quantity)  # Total cost
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

        # Return action to open list view
        return {
            'name': f'Sales Product Profit Report ({len(report_data)} products)',
            'type': 'ir.actions.act_window',
            'res_model': 'product.profit.margin.report',
            'view_mode': 'list',
            'domain': [('id', 'in', report_data)],
            'target': 'current',
            'context': {
                'report_title': f'Sales Product Profit Report [{self.form_type.replace("_", " ").title()}/{self.report_type.title()}] Between {self.date_from} To {self.date_to}'
            }
        }
# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


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
            self.date_from = today - fields.timedelta(days=7)
            self.date_to = today
        elif self.filter_type == 'two_week':
            self.date_from = today - fields.timedelta(days=14)
            self.date_to = today
        elif self.filter_type == 'one_month':
            self.date_from = today - fields.timedelta(days=30)
            self.date_to = today
        elif self.filter_type == 'two_month':
            self.date_from = today - fields.timedelta(days=60)
            self.date_to = today
        elif self.filter_type == 'quarterly':
            self.date_from = today - fields.timedelta(days=90)
            self.date_to = today
        elif self.filter_type == 'six_month':
            self.date_from = today - fields.timedelta(days=180)
            self.date_to = today
        elif self.filter_type == 'one_year':
            self.date_from = today - fields.timedelta(days=365)
            self.date_to = today

    def action_show_report(self):
        """Generate and show the profit margin report"""
        self.ensure_one()

        if self.date_from > self.date_to:
            raise UserError('From date cannot be greater than To date!')

        # Build domain for filtering
        domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('state', '=', 'sale'),
        ]

        # Apply product filter
        if self.product_filter == 'by_group' and self.group_id:
            domain.append(('product_id.categ_id', '=', self.group_id.id))
        elif self.product_filter == 'by_product' and self.product_id:
            domain.append(('product_id', '=', self.product_id.id))

        # Get sale order lines
        sale_lines = self.env['sale.order.line'].search(domain)

        # Prepare report data
        report_data = []
        product_data = {}

        for line in sale_lines:
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
                    'date': line.order_id.date_order,
                    'order_ref': line.order_id.name,
                    'qty': 0.0,
                    'uom': product.uom_id.name,
                    'rate': 0.0,
                    'total': 0.0,
                    'unit_cost': product.standard_price,
                    'total_cost': 0.0,
                    'profit': 0.0,
                }

            product_data[key]['qty'] += line.product_uom_qty
            product_data[key]['total'] += line.price_subtotal
            product_data[key]['rate'] = line.price_unit
            product_data[key]['total_cost'] += (product.standard_price * line.product_uom_qty)
            product_data[key]['profit'] = product_data[key]['total'] - product_data[key]['total_cost']

        # Convert to list
        for data in product_data.values():
            report_line = self.env['product.profit.margin.report'].create(data)
            report_data.append(report_line.id)

        # Return action to open tree view
        return {
            'name': 'Sales Product Profit Report',
            'type': 'ir.actions.act_window',
            'res_model': 'product.profit.margin.report',
            'view_mode': 'tree',
            'domain': [('id', 'in', report_data)],
            'target': 'current',
            'context': {
                'report_title': f'Sales Product Profit Report [{self.form_type.replace("_", " ").title()}/{self.report_type.title()}] Between {self.date_from} To {self.date_to}'
            }
        }
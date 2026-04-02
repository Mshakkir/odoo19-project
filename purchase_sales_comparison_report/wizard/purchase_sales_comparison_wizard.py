# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class PurchaseSalesComparisonWizard(models.TransientModel):
    _name = 'purchase.sales.comparison.wizard'
    _description = 'Purchase Sales Comparison Report Wizard'

    form_type = fields.Selection([
        ('default', 'Default'),
        ('detailed', 'Detailed'),
    ], string='Form Type', default='default', required=True)

    bill_mode = fields.Selection([
        ('all', 'All'),
        ('billed', 'Billed'),
        ('unbilled', 'Unbilled'),
    ], string='Bill Mode', default='all')

    product_filter = fields.Selection([
        ('all', 'All'),
        ('by_product', 'By Product'),
    ], string='Product Filter', default='all', required=True)

    product_id = fields.Many2one('product.product', string='Product')

    date_from = fields.Date(string='From', required=True, default=fields.Date.context_today)
    date_to = fields.Date(string='To', required=True, default=fields.Date.context_today)

    line_ids = fields.One2many(
        'purchase.sales.comparison.line', 'wizard_id', string='Lines'
    )

    @api.onchange('product_filter')
    def _onchange_product_filter(self):
        if self.product_filter == 'all':
            self.product_id = False

    def action_show_report(self):
        self.ensure_one()
        if self.date_from > self.date_to:
            raise UserError('From date cannot be greater than To date.')

        # Clear old lines
        self.line_ids.unlink()

        # Compute lines
        lines = self._compute_lines()

        # Create transient line records
        for line in lines:
            self.env['purchase.sales.comparison.line'].create({
                'wizard_id': self.id,
                'code': line['code'],
                'product_name': line['name'],
                'uom': line['uom'],
                'pur_qty': line['pur_qty'],
                'pur_total': line['pur_total'],
                'sal_qty': line['sal_qty'],
                'sal_total': line['sal_total'],
                'balance_qty': line['balance_qty'],
                'diff_amount': line['diff_amount'],
            })

        # Return action to open results window
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Sales Comparison Report',
            'res_model': 'purchase.sales.comparison.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref(
                'purchase_sales_comparison_report.view_psc_result_form'
            ).id,
            'target': 'new',
        }

    def _compute_lines(self):
        # Purchase lines
        pur_domain = [
            ('order_id.state', 'in', ['purchase', 'done']),
            ('order_id.date_approve', '>=', self.date_from),
            ('order_id.date_approve', '<=', self.date_to),
        ]
        if self.product_filter == 'by_product' and self.product_id:
            pur_domain.append(('product_id', '=', self.product_id.id))
        if self.bill_mode == 'billed':
            pur_domain.append(('qty_invoiced', '>', 0))
        elif self.bill_mode == 'unbilled':
            pur_domain.append(('qty_invoiced', '=', 0))

        purchase_lines = self.env['purchase.order.line'].search(pur_domain)

        # Sales lines
        sal_domain = [
            ('order_id.state', 'in', ['sale', 'done']),
            ('order_id.date_order', '>=', self.date_from),
            ('order_id.date_order', '<=', self.date_to),
        ]
        if self.product_filter == 'by_product' and self.product_id:
            sal_domain.append(('product_id', '=', self.product_id.id))
        if self.bill_mode == 'billed':
            sal_domain.append(('qty_invoiced', '>', 0))
        elif self.bill_mode == 'unbilled':
            sal_domain.append(('qty_invoiced', '=', 0))

        sale_lines = self.env['sale.order.line'].search(sal_domain)

        product_data = {}

        for line in purchase_lines:
            pid = line.product_id.id
            if pid not in product_data:
                product_data[pid] = self._empty_row(line.product_id)
            product_data[pid]['pur_qty'] += line.product_qty
            product_data[pid]['pur_total'] += line.price_subtotal

        for line in sale_lines:
            pid = line.product_id.id
            if pid not in product_data:
                product_data[pid] = self._empty_row(line.product_id)
            product_data[pid]['sal_qty'] += line.product_uom_qty
            product_data[pid]['sal_total'] += line.price_subtotal

        result = []
        for pid, row in sorted(product_data.items(), key=lambda x: x[1]['name']):
            row['balance_qty'] = row['pur_qty'] - row['sal_qty']
            row['diff_amount'] = row['pur_total'] - row['sal_total']
            result.append(row)

        return result

    def _empty_row(self, product):
        return {
            'code': product.default_code or '',
            'name': product.display_name or '',
            'uom': product.uom_id.name if product.uom_id else '',
            'pur_qty': 0.0,
            'pur_total': 0.0,
            'sal_qty': 0.0,
            'sal_total': 0.0,
            'balance_qty': 0.0,
            'diff_amount': 0.0,
        }

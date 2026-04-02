# -*- coding: utf-8 -*-
from odoo import models, api


class PurchaseSalesComparisonReport(models.AbstractModel):
    _name = 'report.purchase_sales_comparison_report.report_purchase_sales_comparison'
    _description = 'Purchase Sales Comparison Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data:
            data = {}

        date_from = data.get('date_from')
        date_to = data.get('date_to')
        product_filter = data.get('product_filter', 'all')
        product_id = data.get('product_id', False)
        bill_mode = data.get('bill_mode', 'all')
        form_type = data.get('form_type', 'default')

        lines = self._get_comparison_lines(
            date_from, date_to, product_filter, product_id, bill_mode
        )

        return {
            'doc_ids': docids,
            'doc_model': 'purchase.sales.comparison.wizard',
            'data': data,
            'lines': lines,
            'date_from': date_from,
            'date_to': date_to,
            'form_type': form_type,
            'bill_mode': bill_mode,
        }

    def _get_comparison_lines(self, date_from, date_to, product_filter, product_id, bill_mode):
        """
        Compute purchase and sales comparison per product.
        Returns list of dicts with keys:
          code, name, uom, pur_qty, pur_total, sal_qty, sal_total, balance_qty, diff_amount
        """
        env = self.env

        # ── Purchase lines (confirmed/done POs) ──────────────────────────────
        pur_domain = [
            ('order_id.state', 'in', ['purchase', 'done']),
            ('order_id.date_approve', '>=', date_from),
            ('order_id.date_approve', '<=', date_to),
        ]
        if product_filter == 'by_product' and product_id:
            pur_domain.append(('product_id', '=', product_id))

        if bill_mode == 'billed':
            pur_domain.append(('qty_invoiced', '>', 0))
        elif bill_mode == 'unbilled':
            pur_domain.append(('qty_invoiced', '=', 0))

        purchase_lines = env['purchase.order.line'].search(pur_domain)

        # ── Sales lines (confirmed/done SOs) ─────────────────────────────────
        sal_domain = [
            ('order_id.state', 'in', ['sale', 'done']),
            ('order_id.date_order', '>=', date_from),
            ('order_id.date_order', '<=', date_to),
        ]
        if product_filter == 'by_product' and product_id:
            sal_domain.append(('product_id', '=', product_id))

        if bill_mode == 'billed':
            sal_domain.append(('qty_invoiced', '>', 0))
        elif bill_mode == 'unbilled':
            sal_domain.append(('qty_invoiced', '=', 0))

        sale_lines = env['sale.order.line'].search(sal_domain)

        # ── Aggregate by product ──────────────────────────────────────────────
        product_data = {}

        for line in purchase_lines:
            pid = line.product_id.id
            if pid not in product_data:
                product_data[pid] = self._empty_product_row(line.product_id)
            product_data[pid]['pur_qty'] += line.product_qty
            product_data[pid]['pur_total'] += line.price_subtotal

        for line in sale_lines:
            pid = line.product_id.id
            if pid not in product_data:
                product_data[pid] = self._empty_product_row(line.product_id)
            product_data[pid]['sal_qty'] += line.product_uom_qty
            product_data[pid]['sal_total'] += line.price_subtotal

        # ── Compute balance & diff ────────────────────────────────────────────
        lines = []
        for pid, row in sorted(product_data.items(), key=lambda x: x[1]['name']):
            row['balance_qty'] = row['pur_qty'] - row['sal_qty']
            row['diff_amount'] = row['pur_total'] - row['sal_total']
            lines.append(row)

        return lines

    def _empty_product_row(self, product):
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

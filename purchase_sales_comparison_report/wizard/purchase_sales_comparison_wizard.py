# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


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
    line_ids = fields.One2many('purchase.sales.comparison.line', 'wizard_id', string='Lines')

    @api.onchange('product_filter')
    def _onchange_product_filter(self):
        if self.product_filter == 'all':
            self.product_id = False

    def action_show_report(self):
        self.ensure_one()
        if self.date_from > self.date_to:
            raise UserError('From date cannot be greater than To date.')

        self.line_ids.unlink()

        lines = self._compute_lines()
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

        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Sales Comparison Report',
            'res_model': 'purchase.sales.comparison.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref(
                'purchase_sales_comparison_report.view_psc_result_form'
            ).id,
            'target': 'main',
        }

    def _get_manual_rate(self, record, company):
        """
        Get manual currency rate from PO/Invoice record.
        Priority:
          1. manual_currency_rate field on the record (from purchase_order_awb or similar module)
          2. res.currency.rate table (inverse_company_rate)
          3. Odoo built-in currency._convert()
        Returns a multiplier: amount_in_foreign * rate = amount_in_company_currency
        """
        company_currency = company.currency_id
        record_currency = getattr(record, 'currency_id', None) or company_currency

        if record_currency == company_currency:
            return 1.0

        # 1. Manual rate set directly on the record
        if hasattr(record, 'manual_currency_rate') and record.manual_currency_rate:
            return float(record.manual_currency_rate)

        # 2. Rate from res.currency.rate table
        rate_date = None
        if hasattr(record, 'date_approve') and record.date_approve:
            rate_date = record.date_approve
        elif hasattr(record, 'date_order') and record.date_order:
            rate_date = record.date_order
            if hasattr(rate_date, 'date'):
                rate_date = rate_date.date()
        elif hasattr(record, 'invoice_date') and record.invoice_date:
            rate_date = record.invoice_date

        if not rate_date:
            rate_date = fields.Date.today()

        rate_record = self.env['res.currency.rate'].search([
            ('currency_id', '=', record_currency.id),
            ('company_id', '=', company.id),
            ('name', '<=', str(rate_date)),
        ], order='name desc', limit=1)

        if rate_record:
            # inverse_company_rate = how many company currency per 1 foreign unit
            if hasattr(rate_record, 'inverse_company_rate') and rate_record.inverse_company_rate:
                return float(rate_record.inverse_company_rate)
            # fallback: rate field = foreign per 1 company currency → invert it
            if rate_record.rate:
                return 1.0 / float(rate_record.rate)

        # 3. Odoo built-in conversion as last resort
        try:
            converted = record_currency._convert(
                1.0, company_currency, company, rate_date
            )
            return converted
        except Exception:
            return 1.0

    def _apply_rate(self, amount, record, company):
        """Convert amount from record currency to company currency."""
        rate = self._get_manual_rate(record, company)
        return amount * rate

    def _compute_lines(self):
        product_data = {}
        company = self.env.company

        # ── 1. Purchase Order Lines ───────────────────────────────────────────
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

        for line in self.env['purchase.order.line'].search(pur_domain):
            pid = line.product_id.id
            if pid not in product_data:
                product_data[pid] = self._empty_row(line.product_id)
            product_data[pid]['pur_qty'] += line.product_qty
            product_data[pid]['pur_total'] += self._apply_rate(
                line.price_subtotal, line.order_id, company
            )

        # ── 2. Vendor Bill Lines (direct — not linked to PO) ─────────────────
        bill_domain = [
            ('move_id.move_type', '=', 'in_invoice'),
            ('move_id.state', '=', 'posted'),
            ('move_id.invoice_date', '>=', self.date_from),
            ('move_id.invoice_date', '<=', self.date_to),
            ('purchase_line_id', '=', False),
            ('product_id', '!=', False),
            ('display_type', '=', 'product'),
        ]
        if self.product_filter == 'by_product' and self.product_id:
            bill_domain.append(('product_id', '=', self.product_id.id))

        for line in self.env['account.move.line'].search(bill_domain):
            pid = line.product_id.id
            if pid not in product_data:
                product_data[pid] = self._empty_row(line.product_id)
            product_data[pid]['pur_qty'] += line.quantity
            product_data[pid]['pur_total'] += self._apply_rate(
                line.price_subtotal, line.move_id, company
            )

        # ── 3. Sales Order Lines ─────────────────────────────────────────────
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

        for line in self.env['sale.order.line'].search(sal_domain):
            pid = line.product_id.id
            if pid not in product_data:
                product_data[pid] = self._empty_row(line.product_id)
            product_data[pid]['sal_qty'] += line.product_uom_qty
            product_data[pid]['sal_total'] += self._apply_rate(
                line.price_subtotal, line.order_id, company
            )

        # ── 4. Customer Invoice Lines (direct — not linked to SO) ────────────
        inv_domain = [
            ('move_id.move_type', '=', 'out_invoice'),
            ('move_id.state', '=', 'posted'),
            ('move_id.invoice_date', '>=', self.date_from),
            ('move_id.invoice_date', '<=', self.date_to),
            ('sale_line_ids', '=', False),
            ('product_id', '!=', False),
            ('display_type', '=', 'product'),
        ]
        if self.product_filter == 'by_product' and self.product_id:
            inv_domain.append(('product_id', '=', self.product_id.id))

        for line in self.env['account.move.line'].search(inv_domain):
            pid = line.product_id.id
            if pid not in product_data:
                product_data[pid] = self._empty_row(line.product_id)
            product_data[pid]['sal_qty'] += line.quantity
            product_data[pid]['sal_total'] += self._apply_rate(
                line.price_subtotal, line.move_id, company
            )

        # ── Compute balance & diff ────────────────────────────────────────────
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
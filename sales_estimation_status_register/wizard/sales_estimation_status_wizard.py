from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta
import base64
import io
import logging

_logger = logging.getLogger(__name__)

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter


class SalesEstimationStatusWizard(models.TransientModel):
    _name = 'sales.estimation.status.wizard'
    _description = 'Sales Estimation Status Register Wizard'

    # ── Type & Filter ──────────────────────────────────────────────────────────
    estimation_type = fields.Selection([
        ('short', 'Short'),
        ('detailed', 'Detailed'),
        ('summary', 'Summary'),
    ], string='Type', default='short', required=True)

    date_filter = fields.Selection([
        ('daily', 'Daily'),
        ('one_week', 'One Week'),
        ('two_week', 'Two Week'),
        ('one_month', 'One Month'),
        ('two_month', 'Two Month'),
        ('quarterly', 'Quarterly'),
        ('six_month', 'Six Month'),
        ('one_year', 'One Year'),
        ('yearly', 'Yearly'),
        ('custom', 'Custom'),
    ], string='Filter', default='daily', required=True)

    # ── Options ────────────────────────────────────────────────────────────────
    form_type = fields.Selection([
        ('quotation', 'Quotation'),
        ('sale_order', 'Sale Order'),
        ('both', 'Both'),
    ], string='Form Type', default=False)

    bill_mode = fields.Selection([
        ('cash', 'Cash'),
        ('credit', 'Credit'),
        ('both', 'Both'),
    ], string='Bill Mode', default=False)

    partner_id = fields.Many2one(
        'res.partner',
        string='Party',
        domain=[('customer_rank', '>', 0)],
    )

    # ── Confirmed Status ───────────────────────────────────────────────────────
    by_confirmed_status = fields.Boolean(string='By Confirmed Status', default=True)
    confirmed = fields.Boolean(string='Confirmed', default=False)

    # ── Cancelled Status ───────────────────────────────────────────────────────
    by_cancelled_status = fields.Boolean(string='By Cancelled Status', default=False)
    cancelled = fields.Boolean(string='Cancelled', default=False)

    # ── Date Range ─────────────────────────────────────────────────────────────
    date_from = fields.Date(
        string='From',
        required=True,
        default=fields.Date.context_today,
    )
    date_to = fields.Date(
        string='To',
        required=True,
        default=fields.Date.context_today,
    )

    # ── Ledger Currency ────────────────────────────────────────────────────────
    use_ledger_currency = fields.Boolean(string='Use Ledger Currency', default=False)

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )

    # ── Date filter onchange ───────────────────────────────────────────────────
    @api.onchange('date_filter')
    def _onchange_date_filter(self):
        today = fields.Date.context_today(self)

        if self.date_filter == 'daily':
            self.date_from = today
            self.date_to = today
        elif self.date_filter == 'one_week':
            self.date_from = today - timedelta(days=6)
            self.date_to = today
        elif self.date_filter == 'two_week':
            self.date_from = today - timedelta(days=13)
            self.date_to = today
        elif self.date_filter == 'one_month':
            self.date_from = today.replace(day=1)
            if today.month == 12:
                self.date_to = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                self.date_to = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
        elif self.date_filter == 'two_month':
            start_month = today.month - 1 if today.month > 1 else 11
            start_year = today.year if today.month > 1 else today.year - 1
            self.date_from = today.replace(year=start_year, month=start_month, day=1)
            if today.month == 12:
                self.date_to = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                self.date_to = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
        elif self.date_filter == 'quarterly':
            quarter_start_month = ((today.month - 1) // 3) * 3 + 1
            self.date_from = today.replace(month=quarter_start_month, day=1)
            end_month = quarter_start_month + 2
            if end_month > 12:
                self.date_to = today.replace(year=today.year + 1, month=end_month - 12, day=1) - timedelta(days=1)
            else:
                self.date_to = today.replace(month=end_month + 1, day=1) - timedelta(days=1) if end_month < 12 else today.replace(month=12, day=31)
        elif self.date_filter == 'six_month':
            self.date_from = today - timedelta(days=180)
            self.date_to = today
        elif self.date_filter == 'one_year':
            self.date_from = today.replace(year=today.year - 1)
            self.date_to = today
        elif self.date_filter == 'yearly':
            self.date_from = today.replace(month=1, day=1)
            self.date_to = today.replace(month=12, day=31)
        # 'custom' → user picks manually, do nothing

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rec in self:
            if rec.date_from > rec.date_to:
                raise UserError(_('From Date must be before To Date.'))

    # ── Data gathering ─────────────────────────────────────────────────────────
    def _build_domain(self):
        domain = [
            ('date_order', '>=', self.date_from),
            ('date_order', '<=', self.date_to),
            ('company_id', '=', self.company_id.id),
        ]

        # Form type / state filter
        if self.form_type == 'quotation':
            domain.append(('state', 'in', ['draft', 'sent']))
        elif self.form_type == 'sale_order':
            domain.append(('state', 'in', ['sale', 'done']))
        else:
            # both
            pass

        # Confirmed / Cancelled filters
        states = []
        if self.by_confirmed_status:
            if self.confirmed:
                states += ['sale', 'done']
            else:
                states += ['draft', 'sent', 'sale', 'done']
        if self.by_cancelled_status:
            if self.cancelled:
                states.append('cancel')
            else:
                if not self.by_confirmed_status:
                    states += ['draft', 'sent', 'sale', 'done', 'cancel']

        if states:
            domain.append(('state', 'in', list(set(states))))

        if self.partner_id:
            domain.append(('partner_id', '=', self.partner_id.id))

        return domain

    def _get_estimation_data(self):
        domain = self._build_domain()
        orders = self.env['sale.order'].search(domain, order='date_order, partner_id')

        data = []
        for order in orders:
            # Bill mode filter (payment term heuristic)
            if self.bill_mode == 'cash':
                if order.payment_term_id and 'credit' in (order.payment_term_id.name or '').lower():
                    continue
            elif self.bill_mode == 'credit':
                if not order.payment_term_id or 'cash' in (order.payment_term_id.name or '').lower():
                    continue

            for line in order.order_line:
                if not line.product_id:
                    continue

                taxes_str = ', '.join(line.tax_id.mapped('name')) if line.tax_id else ''
                tax_amount = line.price_subtotal * sum(line.tax_id.mapped('amount')) / 100 if line.tax_id else 0.0
                total = line.price_subtotal + tax_amount
                discount_amount = (line.price_unit * line.product_uom_qty) * (line.discount / 100) if line.discount else 0.0

                data.append({
                    'date': order.date_order.date(),
                    'estimation_type': dict(self._fields['estimation_type'].selection).get(self.estimation_type, ''),
                    'form_type': 'Quotation' if order.state in ('draft', 'sent') else 'Sale Order',
                    'bill_mode': order.payment_term_id.name if order.payment_term_id else '',
                    'document_number': order.name,
                    'customer_name': order.partner_id.name or '',
                    'customer_vat': order.partner_id.vat or '',
                    'product': line.product_id.name or '',
                    'quantity': line.product_uom_qty,
                    'unit_price': line.price_unit,
                    'subtotal': line.price_subtotal,
                    'discount': discount_amount,
                    'taxes': taxes_str,
                    'tax_amount': tax_amount,
                    'total': total,
                    'state': dict(order._fields['state'].selection).get(order.state, order.state),
                    'currency': order.currency_id.name or '',
                })
        return data

    # ── Actions ────────────────────────────────────────────────────────────────
    def action_show_report(self):
        """Print PDF Report"""
        self.ensure_one()
        data = self._get_estimation_data()
        if not data:
            raise UserError(_('No data found for the selected criteria.'))
        return self.env.ref(
            'sales_estimation_status_register.action_report_sales_estimation_status'
        ).report_action(self)

    def action_show_details(self):
        """Show details in tree view"""
        self.ensure_one()
        data = self._get_estimation_data()
        if not data:
            raise UserError(_('No data found for the selected criteria.'))

        # Clear old records for this wizard
        self.env['sales.estimation.status.details'].search(
            [('wizard_id', '=', self.id)]
        ).unlink()

        detail_ids = []
        for rec in data:
            detail = self.env['sales.estimation.status.details'].create({
                'wizard_id': self.id,
                'date': rec.get('date'),
                'estimation_type': rec.get('estimation_type', ''),
                'form_type': rec.get('form_type', ''),
                'bill_mode': rec.get('bill_mode', ''),
                'document_number': rec.get('document_number', ''),
                'customer_name': rec.get('customer_name', ''),
                'customer_vat': rec.get('customer_vat', ''),
                'product': rec.get('product', ''),
                'quantity': rec.get('quantity', 0),
                'unit_price': rec.get('unit_price', 0),
                'subtotal': rec.get('subtotal', 0),
                'discount': rec.get('discount', 0),
                'taxes': rec.get('taxes', ''),
                'tax_amount': rec.get('tax_amount', 0),
                'total': rec.get('total', 0),
                'state': rec.get('state', ''),
                'currency': rec.get('currency', ''),
                'use_ledger_currency': self.use_ledger_currency,
            })
            detail_ids.append(detail.id)

        return {
            'name': _('Sales Estimation Status Details'),
            'type': 'ir.actions.act_window',
            'res_model': 'sales.estimation.status.details',
            'view_mode': 'list,form',
            'views': [
                (self.env.ref(
                    'sales_estimation_status_register.view_sales_estimation_status_details_tree'
                ).id, 'list')
            ],
            'domain': [('id', 'in', detail_ids)],
            'context': {'create': False, 'edit': False, 'delete': False},
            'target': 'current',
        }

    # ── Quick-filter shortcut buttons ─────────────────────────────────────────
    def _set_filter(self, filter_value):
        self.date_filter = filter_value
        self._onchange_date_filter()
        return {'type': 'ir.actions.act_window',
                'res_model': self._name,
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new'}

    def _set_filter_daily(self):      return self._set_filter('daily')
    def _set_filter_one_week(self):   return self._set_filter('one_week')
    def _set_filter_two_week(self):   return self._set_filter('two_week')
    def _set_filter_one_month(self):  return self._set_filter('one_month')
    def _set_filter_two_month(self):  return self._set_filter('two_month')
    def _set_filter_quarterly(self):  return self._set_filter('quarterly')
    def _set_filter_six_month(self):  return self._set_filter('six_month')
    def _set_filter_one_year(self):   return self._set_filter('one_year')
    def _set_filter_yearly(self):     return self._set_filter('yearly')

    def action_export_excel(self):
        """Export to Excel"""
        self.ensure_one()
        data = self._get_estimation_data()
        if not data:
            raise UserError(_('No data found for the selected criteria.'))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        ws = workbook.add_worksheet('Sales Estimation Status')

        title_fmt = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center'})
        header_fmt = workbook.add_format({
            'bold': True, 'bg_color': '#4472C4', 'font_color': 'white',
            'border': 1, 'align': 'center',
        })
        date_fmt = workbook.add_format({'num_format': 'dd/mm/yyyy'})
        num_fmt = workbook.add_format({'num_format': '#,##0.00'})
        total_fmt = workbook.add_format({'bold': True, 'bg_color': '#D9E1F2', 'border': 1, 'num_format': '#,##0.00'})

        ws.merge_range('A1:O1', 'SALES ESTIMATION STATUS REGISTER', title_fmt)
        ws.merge_range('A2:O2', self.company_id.name, title_fmt)
        ws.merge_range('A3:O3',
            f'Period: {self.date_from.strftime("%d/%m/%Y")} to {self.date_to.strftime("%d/%m/%Y")}',
            title_fmt)

        headers = [
            'Date', 'Type', 'Form Type', 'Bill Mode', 'Document No.',
            'Party', 'VAT/TRN', 'Product', 'Qty', 'Unit Price',
            'Subtotal', 'Discount', 'Tax', 'Tax Amount', 'Total', 'Status', 'Currency',
        ]
        for col, h in enumerate(headers):
            ws.write(4, col, h, header_fmt)

        row = 5
        totals = {k: 0.0 for k in ['subtotal', 'discount', 'tax_amount', 'total']}
        for rec in data:
            ws.write_datetime(row, 0, rec['date'], date_fmt)
            ws.write(row, 1, rec['estimation_type'])
            ws.write(row, 2, rec['form_type'])
            ws.write(row, 3, rec['bill_mode'])
            ws.write(row, 4, rec['document_number'])
            ws.write(row, 5, rec['customer_name'])
            ws.write(row, 6, rec['customer_vat'])
            ws.write(row, 7, rec['product'])
            ws.write(row, 8, rec['quantity'])
            ws.write(row, 9, rec['unit_price'], num_fmt)
            ws.write(row, 10, rec['subtotal'], num_fmt)
            ws.write(row, 11, rec['discount'], num_fmt)
            ws.write(row, 12, rec['taxes'])
            ws.write(row, 13, rec['tax_amount'], num_fmt)
            ws.write(row, 14, rec['total'], num_fmt)
            ws.write(row, 15, rec['state'])
            ws.write(row, 16, rec['currency'])
            for k in totals:
                totals[k] += rec.get(k, 0)
            row += 1

        ws.write(row, 9, 'TOTAL:', total_fmt)
        ws.write(row, 10, totals['subtotal'], total_fmt)
        ws.write(row, 11, totals['discount'], total_fmt)
        ws.write(row, 13, totals['tax_amount'], total_fmt)
        ws.write(row, 14, totals['total'], total_fmt)

        ws.set_column('A:A', 12)
        ws.set_column('B:D', 14)
        ws.set_column('E:E', 16)
        ws.set_column('F:G', 22)
        ws.set_column('H:H', 28)
        ws.set_column('I:Q', 12)

        workbook.close()
        output.seek(0)

        attachment = self.env['ir.attachment'].create({
            'name': f'Sales_Estimation_Status_{self.date_from}_{self.date_to}.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(output.read()),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }
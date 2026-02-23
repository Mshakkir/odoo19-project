from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta, datetime
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
    ], string='Filter', default='custom', required=True)

    form_type = fields.Selection([
        ('quotation', 'Quotation'),
        ('sale_order', 'Sale Order'),
        ('both', 'Both'),
    ], string='Form Type', default='both')

    bill_mode = fields.Selection([
        ('cash', 'Cash'),
        ('credit', 'Credit'),
        ('both', 'Both'),
    ], string='Bill Mode', default='both')

    partner_id = fields.Many2one(
        'res.partner',
        string='Party',
        domain=[('customer_rank', '>', 0)],
    )

    by_confirmed_status = fields.Boolean(string='By Confirmed Status', default=False)
    confirmed = fields.Boolean(string='Confirmed', default=False)
    by_cancelled_status = fields.Boolean(string='By Cancelled Status', default=False)
    cancelled = fields.Boolean(string='Cancelled', default=False)

    date_from = fields.Date(
        string='From',
        required=True,
        default=lambda self: fields.Date.context_today(self).replace(day=1),
    )
    date_to = fields.Date(
        string='To',
        required=True,
        default=fields.Date.context_today,
    )

    use_ledger_currency = fields.Boolean(string='Use Ledger Currency', default=False)

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )

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
            m = today.month - 2
            y = today.year
            if m <= 0:
                m += 12
                y -= 1
            self.date_from = today.replace(year=y, month=m, day=1)
            self.date_to = today
        elif self.date_filter == 'quarterly':
            qsm = ((today.month - 1) // 3) * 3 + 1
            self.date_from = today.replace(month=qsm, day=1)
            em = qsm + 2
            if em == 12:
                self.date_to = today.replace(month=12, day=31)
            elif em > 12:
                self.date_to = today.replace(year=today.year + 1, month=em - 12 + 1, day=1) - timedelta(days=1)
            else:
                self.date_to = today.replace(month=em + 1, day=1) - timedelta(days=1)
        elif self.date_filter == 'six_month':
            self.date_from = today - timedelta(days=180)
            self.date_to = today
        elif self.date_filter == 'one_year':
            self.date_from = today.replace(year=today.year - 1)
            self.date_to = today
        elif self.date_filter == 'yearly':
            self.date_from = today.replace(month=1, day=1)
            self.date_to = today.replace(month=12, day=31)

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_from > rec.date_to:
                raise UserError(_('From Date must be before or equal to To Date.'))

    def _build_domain(self):
        date_from_dt = datetime.combine(self.date_from, datetime.min.time())
        date_to_dt = datetime.combine(self.date_to, datetime.max.time())

        domain = [
            ('date_order', '>=', date_from_dt),
            ('date_order', '<=', date_to_dt),
            ('company_id', '=', self.company_id.id),
        ]

        if self.form_type == 'quotation':
            allowed = {'draft', 'sent'}
        elif self.form_type == 'sale_order':
            allowed = {'sale', 'done'}
        else:
            allowed = {'draft', 'sent', 'sale', 'done'}

        if self.by_confirmed_status and self.confirmed:
            allowed &= {'sale', 'done'}

        if self.by_cancelled_status and self.cancelled:
            allowed = {'cancel'}
        else:
            allowed.discard('cancel')

        domain.append(('state', 'in', list(allowed)))

        if self.partner_id:
            domain.append(('partner_id', '=', self.partner_id.id))

        _logger.info("Sales Estimation domain: %s | states: %s", domain, allowed)
        return domain

    def _get_address(self, partner):
        """Build a single address string from partner fields."""
        parts = []
        if partner.street:
            parts.append(partner.street)
        if partner.street2:
            parts.append(partner.street2)
        if partner.city:
            parts.append(partner.city)
        if partner.state_id:
            parts.append(partner.state_id.name)
        if partner.country_id:
            parts.append(partner.country_id.name)
        return ', '.join(filter(None, parts))

    def _get_cell_no(self, partner):
        """Return mobile first, then phone."""
        return partner.mobile or partner.phone or ''

    def _get_sales_account(self, line):
        """Return the sales/income account for the product line."""
        if not line or not line.product_id:
            return ''
        # Try product's income account first
        product = line.product_id
        account = None
        try:
            account = product.property_account_income_id
        except Exception:
            pass
        if not account:
            try:
                account = product.categ_id.property_account_income_categ_id
            except Exception:
                pass
        return account.code + ' ' + account.name if account else ''

    def _get_warehouse(self, order):
        """Return warehouse name from the sale order."""
        try:
            if order.warehouse_id:
                return order.warehouse_id.name
        except Exception:
            pass
        return ''

    def _get_estimation_data(self):
        domain = self._build_domain()
        orders = self.env['sale.order'].search(domain, order='date_order asc, name asc')
        _logger.info("Sales Estimation: %d orders found", len(orders))

        data = []
        for order in orders:
            if self.bill_mode and self.bill_mode != 'both':
                has_delay = False
                if order.payment_term_id and order.payment_term_id.line_ids:
                    has_delay = any(
                        getattr(ln, 'nb_days', 0) > 0
                        for ln in order.payment_term_id.line_ids
                    )
                if self.bill_mode == 'cash' and has_delay:
                    continue
                if self.bill_mode == 'credit' and not has_delay:
                    continue

            lines = order.order_line.filtered(
                lambda l: l.display_type not in ('line_section', 'line_note')
            )

            if not lines:
                data.append(self._build_row(order, None))
            else:
                for line in lines:
                    data.append(self._build_row(order, line))

        return data

    def _build_row(self, order, line):
        # ── New custom fields ──────────────────────────────────────────────────
        partner = order.partner_id
        address = self._get_address(partner)
        cell_no = self._get_cell_no(partner)
        warehouse = self._get_warehouse(order)
        sales_account = self._get_sales_account(line)

        # ── Line-level fields ─────────────────────────────────────────────────
        if line:
            try:
                taxes = line.tax_ids
            except AttributeError:
                try:
                    taxes = line.tax_id
                except AttributeError:
                    taxes = False

            taxes_str = ', '.join(taxes.mapped('name')) if taxes else ''
            tax_amount = getattr(line, 'price_tax', 0.0) or 0.0
            subtotal = getattr(line, 'price_subtotal', 0.0) or 0.0
            price_total = getattr(line, 'price_total', None)
            total = price_total if (price_total is not None) else (subtotal + tax_amount)
            qty = getattr(line, 'product_uom_qty', 0.0) or 0.0
            unit_price = getattr(line, 'price_unit', 0.0) or 0.0
            product_name = (line.product_id.name if line.product_id else '') or (line.name or '')
            discount_pct = getattr(line, 'discount', 0.0) or 0.0
            discount_amount = (unit_price * qty) * (discount_pct / 100.0) if discount_pct else 0.0
        else:
            taxes_str = ''
            tax_amount = order.amount_tax or 0.0
            subtotal = order.amount_untaxed or 0.0
            total = order.amount_total or 0.0
            qty = 0.0
            unit_price = 0.0
            product_name = ''
            discount_amount = 0.0

        state_label = dict(order._fields['state'].selection).get(order.state, order.state)
        form_label = 'Quotation' if order.state in ('draft', 'sent') else 'Sale Order'
        type_label = dict(self._fields['estimation_type'].selection).get(
            self.estimation_type, self.estimation_type
        )

        return {
            # ── NEW columns (first) ───────────────────────────────────────────
            'date': order.date_order.date() if order.date_order else False,
            'vno': order.name or '',
            'warehouse': warehouse,
            'customer_name': partner.name or '',
            'address': address,
            'cell_no': cell_no,
            'sales_account': sales_account,
            # ── Existing columns ──────────────────────────────────────────────
            'estimation_type': type_label,
            'form_type': form_label,
            'bill_mode': order.payment_term_id.name if order.payment_term_id else 'Immediate',
            'document_number': order.name or '',
            'customer_vat': partner.vat or '',
            'product': product_name,
            'quantity': qty,
            'unit_price': unit_price,
            'subtotal': subtotal,
            'discount': discount_amount,
            'taxes': taxes_str,
            'tax_amount': tax_amount,
            'total': total,
            'state': state_label,
            'currency': order.currency_id.name or '',
        }

    def _no_data_error(self):
        raise UserError(_(
            'No data found for the selected criteria.\n\n'
            'Suggestions:\n'
            '  • Set Form Type to "Both"\n'
            '  • Use a wider date range (One Year / Yearly)\n'
            '  • Uncheck "By Confirmed Status" and "By Cancelled Status"\n'
            '  • Clear the Party filter to include all customers'
        ))

    def action_show_report(self):
        self.ensure_one()
        data = self._get_estimation_data()
        if not data:
            self._no_data_error()
        return self.env.ref(
            'sales_estimation_status_register.action_report_sales_estimation_status'
        ).report_action(self)

    def action_show_details(self):
        self.ensure_one()
        data = self._get_estimation_data()
        if not data:
            self._no_data_error()

        self.env['sales.estimation.status.details'].search(
            [('wizard_id', '=', self.id)]
        ).unlink()

        detail_ids = []
        for rec in data:
            detail = self.env['sales.estimation.status.details'].create({
                'wizard_id': self.id,
                'date': rec.get('date'),
                'vno': rec.get('vno', ''),
                'warehouse': rec.get('warehouse', ''),
                'customer_name': rec.get('customer_name', ''),
                'address': rec.get('address', ''),
                'cell_no': rec.get('cell_no', ''),
                'sales_account': rec.get('sales_account', ''),
                'estimation_type': rec.get('estimation_type', ''),
                'form_type': rec.get('form_type', ''),
                'bill_mode': rec.get('bill_mode', ''),
                'document_number': rec.get('document_number', ''),
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

    def action_export_excel(self):
        self.ensure_one()
        data = self._get_estimation_data()
        if not data:
            self._no_data_error()

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        ws = workbook.add_worksheet('Sales Estimation Status')

        title_fmt = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center', 'valign': 'vcenter'})
        header_fmt = workbook.add_format({'bold': True, 'bg_color': '#4472C4', 'font_color': 'white', 'border': 1, 'align': 'center', 'valign': 'vcenter', 'text_wrap': True})
        date_fmt = workbook.add_format({'num_format': 'dd/mm/yyyy', 'border': 1})
        num_fmt = workbook.add_format({'num_format': '#,##0.00', 'border': 1})
        text_fmt = workbook.add_format({'border': 1})
        total_fmt = workbook.add_format({'bold': True, 'bg_color': '#D9E1F2', 'border': 1, 'num_format': '#,##0.00'})
        total_label_fmt = workbook.add_format({'bold': True, 'bg_color': '#D9E1F2', 'border': 1, 'align': 'right'})

        # 24 columns total (A to X)
        last_col = 'X'
        ws.set_row(0, 22)
        ws.set_row(4, 30)
        ws.merge_range(f'A1:{last_col}1', 'SALES ESTIMATION STATUS REGISTER', title_fmt)
        ws.merge_range(f'A2:{last_col}2', self.company_id.name, title_fmt)
        ws.merge_range(f'A3:{last_col}3',
            f'Period: {self.date_from.strftime("%d/%m/%Y")} to {self.date_to.strftime("%d/%m/%Y")}',
            title_fmt)

        headers = [
            # New first columns
            'Date', 'Vno', 'Warehouse', 'Customer Name', 'Address', 'Cell No', 'Sales Account',
            # Existing columns
            'Type', 'Form Type', 'Bill Mode', 'Document No.',
            'VAT/TRN', 'Product', 'Qty', 'Unit Price',
            'Subtotal', 'Discount', 'Tax', 'Tax Amount', 'Total', 'Status', 'Currency',
        ]
        for col, h in enumerate(headers):
            ws.write(4, col, h, header_fmt)

        row = 5
        totals = {k: 0.0 for k in ['subtotal', 'discount', 'tax_amount', 'total']}

        for rec in data:
            date_val = rec.get('date')
            if date_val:
                ws.write_datetime(row, 0, datetime.combine(date_val, datetime.min.time()), date_fmt)
            else:
                ws.write(row, 0, '', text_fmt)

            ws.write(row, 1,  rec.get('vno', ''),            text_fmt)
            ws.write(row, 2,  rec.get('warehouse', ''),       text_fmt)
            ws.write(row, 3,  rec.get('customer_name', ''),   text_fmt)
            ws.write(row, 4,  rec.get('address', ''),         text_fmt)
            ws.write(row, 5,  rec.get('cell_no', ''),         text_fmt)
            ws.write(row, 6,  rec.get('sales_account', ''),   text_fmt)
            ws.write(row, 7,  rec.get('estimation_type', ''), text_fmt)
            ws.write(row, 8,  rec.get('form_type', ''),       text_fmt)
            ws.write(row, 9,  rec.get('bill_mode', ''),       text_fmt)
            ws.write(row, 10, rec.get('document_number', ''), text_fmt)
            ws.write(row, 11, rec.get('customer_vat', ''),    text_fmt)
            ws.write(row, 12, rec.get('product', ''),         text_fmt)
            ws.write(row, 13, rec.get('quantity', 0),         num_fmt)
            ws.write(row, 14, rec.get('unit_price', 0),       num_fmt)
            ws.write(row, 15, rec.get('subtotal', 0),         num_fmt)
            ws.write(row, 16, rec.get('discount', 0),         num_fmt)
            ws.write(row, 17, rec.get('taxes', ''),           text_fmt)
            ws.write(row, 18, rec.get('tax_amount', 0),       num_fmt)
            ws.write(row, 19, rec.get('total', 0),            num_fmt)
            ws.write(row, 20, rec.get('state', ''),           text_fmt)
            ws.write(row, 21, rec.get('currency', ''),        text_fmt)

            totals['subtotal']   += rec.get('subtotal', 0)
            totals['discount']   += rec.get('discount', 0)
            totals['tax_amount'] += rec.get('tax_amount', 0)
            totals['total']      += rec.get('total', 0)
            row += 1

        ws.write(row, 14, 'TOTAL:',            total_label_fmt)
        ws.write(row, 15, totals['subtotal'],   total_fmt)
        ws.write(row, 16, totals['discount'],   total_fmt)
        ws.write(row, 17, '',                   total_label_fmt)
        ws.write(row, 18, totals['tax_amount'], total_fmt)
        ws.write(row, 19, totals['total'],      total_fmt)

        # Column widths
        ws.set_column(0,  0,  12)  # Date
        ws.set_column(1,  1,  14)  # Vno
        ws.set_column(2,  2,  18)  # Warehouse
        ws.set_column(3,  3,  24)  # Customer Name
        ws.set_column(4,  4,  30)  # Address
        ws.set_column(5,  5,  14)  # Cell No
        ws.set_column(6,  6,  28)  # Sales Account
        ws.set_column(7,  9,  13)  # Type, Form Type, Bill Mode
        ws.set_column(10, 10, 14)  # Document No
        ws.set_column(11, 11, 14)  # VAT/TRN
        ws.set_column(12, 12, 28)  # Product
        ws.set_column(13, 21, 12)  # numeric cols

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
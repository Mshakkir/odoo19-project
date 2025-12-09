from odoo import models, fields, api
from datetime import datetime
from collections import defaultdict


class SalesBookWizard(models.TransientModel):
    _name = 'sales.book.wizard'
    _description = 'Sales Book Report Wizard'

    report_type = fields.Selection([
        ('sales', 'Sales Report'),
        ('return', 'Sales Return Report'),
        ('both', 'Sales & Sales Return Report')
    ], string='Report Type', required=True, default='sales')

    view_type = fields.Selection([
        ('short', 'Short'),
        ('detail', 'Detail')
    ], string='View Type', required=True, default='short')

    filter_type = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
        ('custom', 'Custom')
    ], string='Filter', required=True, default='daily')

    date_from = fields.Date(string='From Date', required=True,
                            default=lambda self: fields.Date.today())
    date_to = fields.Date(string='To Date', required=True,
                          default=lambda self: fields.Date.today())

    partner_ids = fields.Many2many('res.partner', string='Customers')

    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        string='Analytic Accounts',
        help='Filter by Analytic Accounts'
    )

    include_expense = fields.Boolean(string='Include Expense Sales', default=True)

    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)

    # -------------------------------------------------------------
    # DATE FILTER
    # -------------------------------------------------------------
    @api.onchange('filter_type')
    def _onchange_filter_type(self):
        today = fields.Date.today()
        if self.filter_type == 'daily':
            self.date_from = today
            self.date_to = today
        elif self.filter_type == 'monthly':
            self.date_from = today.replace(day=1)
            self.date_to = today
        elif self.filter_type == 'yearly':
            self.date_from = today.replace(month=1, day=1)
            self.date_to = today

    # -------------------------------------------------------------
    # MAIN ENTRY
    # -------------------------------------------------------------
    def action_print_report(self):
        self.ensure_one()
        return self.env.ref('sales_book.action_report_sales_book').report_action(self)

    def _get_report_data(self):
        self.ensure_one()

        if self.report_type == 'sales':
            return self._get_sales_data()

        elif self.report_type == 'return':
            return self._get_return_data()

        else:
            return self._get_combined_data()

    # -------------------------------------------------------------
    # GROUPING FUNCTION (SHORT VIEW)
    # -------------------------------------------------------------
    def _group_short(self, data):
        """Group data by date (short view)."""
        grouped = defaultdict(lambda: {
            'date': None,
            'gross': 0.0,
            'trade_disc': 0.0,
            'net_total': 0.0,
            'add_disc': 0.0,
            'add_cost': 0.0,
            'round_off': 0.0,
            'adj_amount': 0.0,
            'tax_amount': 0.0,
            'grand_total': 0.0,
        })

        for line in data:
            key = line['date']
            g = grouped[key]

            if g['date'] is None:
                g['date'] = line['date']

            g['gross'] += line.get('gross', 0)
            g['trade_disc'] += line.get('trade_disc', 0)
            g['net_total'] += line.get('net_total', 0)
            g['add_disc'] += line.get('add_disc', 0)
            g['add_cost'] += line.get('add_cost', 0)
            g['round_off'] += line.get('round_off', 0)
            g['adj_amount'] += line.get('adj_amount', 0)
            g['tax_amount'] += line.get('tax_amount', 0)
            g['grand_total'] += line.get('grand_total', 0)

        result = list(grouped.values())
        result.sort(key=lambda x: x['date'])
        return result

    def _group_short_combined(self, data):
        """Group combined data by date and type for short view."""
        grouped = defaultdict(lambda: {
            'date': None,
            'type': None,
            'gross': 0.0,
            'trade_disc': 0.0,
            'net_total': 0.0,
            'add_disc': 0.0,
            'add_cost': 0.0,
            'round_off': 0.0,
            'adj_amount': 0.0,
            'tax_amount': 0.0,
            'grand_total': 0.0,
        })

        for line in data:
            # Key is date + type
            key = (line['date'], line.get('type', 'Sales'))
            g = grouped[key]

            if g['date'] is None:
                g['date'] = line['date']
                g['type'] = line.get('type', 'Sales')

            g['gross'] += line.get('gross', 0)
            g['trade_disc'] += line.get('trade_disc', 0)
            g['net_total'] += line.get('net_total', 0)
            g['add_disc'] += line.get('add_disc', 0)
            g['add_cost'] += line.get('add_cost', 0)
            g['round_off'] += line.get('round_off', 0)
            g['adj_amount'] += line.get('adj_amount', 0)
            g['tax_amount'] += line.get('tax_amount', 0)
            g['grand_total'] += line.get('grand_total', 0)

        result = list(grouped.values())
        result.sort(key=lambda x: (x['date'], x['type']))
        return result

    # -------------------------------------------------------------
    # SALES DATA
    # -------------------------------------------------------------
    def _get_sales_data(self):
        self.ensure_one()

        domain = [
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
            ('state', '=', 'posted'),
            ('move_type', '=', 'out_invoice'),
            ('company_id', '=', self.company_id.id),
        ]

        if self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))

        invoices = self.env['account.move'].search(domain, order='invoice_date asc')

        data = []
        for inv in invoices:
            gross = sum(inv.invoice_line_ids.mapped('price_subtotal'))
            trade_disc = 0
            for l in inv.invoice_line_ids:
                if l.discount:
                    trade_disc += (l.price_unit * l.quantity * l.discount) / 100

            net_total = gross - trade_disc
            tax = sum((l.price_total - l.price_subtotal) for l in inv.invoice_line_ids)
            grand = net_total + tax

            data.append({
                'date': inv.invoice_date,
                'customer': inv.partner_id.name,
                'invoice_ref': inv.ref or inv.name,
                'gross': gross,
                'trade_disc': trade_disc,
                'net_total': net_total,
                'add_disc': 0,
                'add_cost': 0,
                'round_off': 0,
                'adj_amount': 0,
                'tax_amount': tax,
                'grand_total': grand,
                'type': 'Sales',
            })

        if self.view_type == 'short':
            return self._group_short(data)

        return data

    # -------------------------------------------------------------
    # RETURN DATA
    # -------------------------------------------------------------
    def _get_return_data(self):
        self.ensure_one()

        domain = [
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
            ('state', '=', 'posted'),
            ('move_type', '=', 'out_refund'),
            ('company_id', '=', self.company_id.id),
        ]

        if self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))

        invoices = self.env['account.move'].search(domain, order='invoice_date asc')

        data = []
        for inv in invoices:
            gross = sum(inv.invoice_line_ids.mapped('price_subtotal'))
            trade_disc = 0
            for l in inv.invoice_line_ids:
                if l.discount:
                    trade_disc += (l.price_unit * l.quantity * l.discount) / 100

            net_total = gross - trade_disc
            tax = sum((l.price_total - l.price_subtotal) for l in inv.invoice_line_ids)
            grand = net_total + tax

            # Return should be NEGATIVE
            data.append({
                'date': inv.invoice_date,
                'customer': inv.partner_id.name,
                'invoice_ref': inv.ref or inv.name,
                'gross': -abs(gross),
                'trade_disc': -abs(trade_disc),
                'net_total': -abs(net_total),
                'add_disc': 0,
                'add_cost': 0,
                'round_off': 0,
                'adj_amount': 0,
                'tax_amount': -abs(tax),
                'grand_total': -abs(grand),
                'type': 'Return',
            })

        if self.view_type == 'short':
            return self._group_short(data)

        return data

    # -------------------------------------------------------------
    # COMBINED DATA (SALES + RETURN)
    # -------------------------------------------------------------
    def _get_combined_data(self):
        # temporarily force detail
        original = self.view_type
        self.view_type = 'detail'

        sales = self._get_sales_data()
        returns = self._get_return_data()

        self.view_type = original  # restore

        combined = sales + returns
        combined.sort(key=lambda x: x['date'])

        if original == 'short':
            return self._group_short_combined(combined)

        return combined

    # -------------------------------------------------------------
    # REPORT VALUES
    # -------------------------------------------------------------
    def _get_report_values(self):
        return {
            'doc_ids': self.ids,
            'doc_model': 'sales.book.wizard',
            'docs': self,
            'data': self._get_report_data(),
            'date_from': self.date_from,
            'date_to': self.date_to,
            'report_type': self.report_type,
            'company': self.company_id,
            'analytic_accounts': self.analytic_account_ids,
        }
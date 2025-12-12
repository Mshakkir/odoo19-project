# -*- coding: utf-8 -*-
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

    # Preview Lines
    preview_line_ids = fields.One2many(
        'sales.book.preview.line',
        'wizard_id',
        string='Preview Lines'
    )

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

    def action_print_report(self):
        self.ensure_one()
        return self.env.ref('sales_book.action_report_sales_book').report_action(self)

    def action_preview(self):
        """Generate preview data and show in tree view"""
        self.ensure_one()

        # Clear existing preview lines
        self.preview_line_ids.unlink()

        # Get report data
        data = self._get_report_data()

        # Create preview lines
        preview_lines = []
        for line in data:
            preview_lines.append((0, 0, {
                'date': line['date'],
                'customer': line.get('customer', ''),
                'invoice_ref': line.get('invoice_ref', ''),
                'transaction_type': line.get('type', 'Sales'),
                'gross': line.get('gross', 0.0),
                'trade_disc': line.get('trade_disc', 0.0),
                'net_total': line.get('net_total', 0.0),
                'add_disc': line.get('add_disc', 0.0),
                'add_cost': line.get('add_cost', 0.0),
                'round_off': line.get('round_off', 0.0),
                'adj_amount': line.get('adj_amount', 0.0),
                'tax_amount': line.get('tax_amount', 0.0),
                'grand_total': line.get('grand_total', 0.0),
            }))

        self.write({'preview_line_ids': preview_lines})

        # Return action to show preview
        return {
            'type': 'ir.actions.act_window',
            'name': self._get_preview_title(),
            'res_model': 'sales.book.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'views': [(self.env.ref('sales_book.view_sales_book_wizard_preview_form').id, 'form')],
            'target': 'new',
            'context': self.env.context,
        }

    def _get_preview_title(self):
        """Get preview window title based on report type"""
        titles = {
            'sales': 'Sales Book Preview',
            'return': 'Sales Return Book Preview',
            'both': 'Sales & Sales Return Book Preview'
        }
        return titles.get(self.report_type, 'Sales Book Preview')

    def _get_report_data(self):
        self.ensure_one()
        if self.report_type == 'sales':
            return self._get_sales_data()
        elif self.report_type == 'return':
            return self._get_return_data()
        else:
            return self._get_combined_data()

    def _group_short(self, data):
        grouped = defaultdict(lambda: {
            'date': None, 'gross': 0.0, 'trade_disc': 0.0, 'net_total': 0.0,
            'add_disc': 0.0, 'add_cost': 0.0, 'round_off': 0.0,
            'adj_amount': 0.0, 'tax_amount': 0.0, 'grand_total': 0.0,
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
        grouped = defaultdict(lambda: {
            'date': None, 'type': None, 'gross': 0.0, 'trade_disc': 0.0,
            'net_total': 0.0, 'add_disc': 0.0, 'add_cost': 0.0, 'round_off': 0.0,
            'adj_amount': 0.0, 'tax_amount': 0.0, 'grand_total': 0.0,
        })
        for line in data:
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
            trade_disc = sum((l.price_unit * l.quantity * l.discount) / 100
                             for l in inv.invoice_line_ids if l.discount)
            net_total = gross - trade_disc
            tax = sum((l.price_total - l.price_subtotal) for l in inv.invoice_line_ids)
            grand = net_total + tax
            data.append({
                'date': inv.invoice_date,
                'customer': inv.partner_id.name,
                'invoice_ref': inv.ref or inv.name,
                'gross': gross, 'trade_disc': trade_disc, 'net_total': net_total,
                'add_disc': 0, 'add_cost': 0, 'round_off': 0, 'adj_amount': 0,
                'tax_amount': tax, 'grand_total': grand, 'type': 'Sales',
            })
        if self.view_type == 'short':
            return self._group_short(data)
        return data

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
            trade_disc = sum((l.price_unit * l.quantity * l.discount) / 100
                             for l in inv.invoice_line_ids if l.discount)
            net_total = gross - trade_disc
            tax = sum((l.price_total - l.price_subtotal) for l in inv.invoice_line_ids)
            grand = net_total + tax
            data.append({
                'date': inv.invoice_date,
                'customer': inv.partner_id.name,
                'invoice_ref': inv.ref or inv.name,
                'gross': -abs(gross), 'trade_disc': -abs(trade_disc),
                'net_total': -abs(net_total), 'add_disc': 0, 'add_cost': 0,
                'round_off': 0, 'adj_amount': 0, 'tax_amount': -abs(tax),
                'grand_total': -abs(grand), 'type': 'Return',
            })
        if self.view_type == 'short':
            return self._group_short(data)
        return data

    def _get_combined_data(self):
        original = self.view_type
        self.view_type = 'detail'
        sales = self._get_sales_data()
        returns = self._get_return_data()
        self.view_type = original
        combined = sales + returns
        combined.sort(key=lambda x: x['date'])
        if original == 'short':
            return self._group_short_combined(combined)
        return combined


class SalesBookPreviewLine(models.TransientModel):
    _name = 'sales.book.preview.line'
    _description = 'Sales Book Preview Line'
    _order = 'date, id'

    wizard_id = fields.Many2one('sales.book.wizard', string='Wizard', required=True, ondelete='cascade')
    date = fields.Date(string='Date', required=True)
    customer = fields.Char(string='Customer')
    invoice_ref = fields.Char(string='Invoice/Ref')
    transaction_type = fields.Selection([
        ('Sales', 'Sales'),
        ('Return', 'Return')
    ], string='Type', default='Sales')
    gross = fields.Float(string='Gross', digits=(16, 2))
    trade_disc = fields.Float(string='Trade Disc', digits=(16, 2))
    net_total = fields.Float(string='Net Total', digits=(16, 2))
    add_disc = fields.Float(string='Add. Disc', digits=(16, 2))
    add_cost = fields.Float(string='Add. Cost', digits=(16, 2))
    round_off = fields.Float(string='Round Off', digits=(16, 2))
    adj_amount = fields.Float(string='Adj. Amount', digits=(16, 2))
    tax_amount = fields.Float(string='Tax Amount', digits=(16, 2))
    grand_total = fields.Float(string='Grand Total', digits=(16, 2))








# # -*- coding: utf-8 -*-
# from odoo import models, fields, api
# from datetime import datetime
# from collections import defaultdict
#
#
# class SalesBookWizard(models.TransientModel):
#     _name = 'sales.book.wizard'
#     _description = 'Sales Book Report Wizard'
#
#     report_type = fields.Selection([
#         ('sales', 'Sales Report'),
#         ('return', 'Sales Return Report'),
#         ('both', 'Sales & Sales Return Report')
#     ], string='Report Type', required=True, default='sales')
#
#     view_type = fields.Selection([
#         ('short', 'Short'),
#         ('detail', 'Detail')
#     ], string='View Type', required=True, default='short')
#
#     filter_type = fields.Selection([
#         ('daily', 'Daily'),
#         ('weekly', 'Weekly'),
#         ('monthly', 'Monthly'),
#         ('yearly', 'Yearly'),
#         ('custom', 'Custom')
#     ], string='Filter', required=True, default='daily')
#
#     date_from = fields.Date(string='From Date', required=True,
#                             default=lambda self: fields.Date.today())
#     date_to = fields.Date(string='To Date', required=True,
#                           default=lambda self: fields.Date.today())
#
#     partner_ids = fields.Many2many('res.partner', string='Customers')
#
#     analytic_account_ids = fields.Many2many(
#         'account.analytic.account',
#         string='Analytic Accounts',
#         help='Filter by Analytic Accounts'
#     )
#
#     include_expense = fields.Boolean(string='Include Expense Sales', default=True)
#
#     company_id = fields.Many2one('res.company', string='Company',
#                                  default=lambda self: self.env.company)
#
#     @api.onchange('filter_type')
#     def _onchange_filter_type(self):
#         today = fields.Date.today()
#         if self.filter_type == 'daily':
#             self.date_from = today
#             self.date_to = today
#         elif self.filter_type == 'monthly':
#             self.date_from = today.replace(day=1)
#             self.date_to = today
#         elif self.filter_type == 'yearly':
#             self.date_from = today.replace(month=1, day=1)
#             self.date_to = today
#
#     def action_print_report(self):
#         self.ensure_one()
#         return self.env.ref('sales_book.action_report_sales_book').report_action(self)
#
#     def _get_report_data(self):
#         self.ensure_one()
#         if self.report_type == 'sales':
#             return self._get_sales_data()
#         elif self.report_type == 'return':
#             return self._get_return_data()
#         else:
#             return self._get_combined_data()
#
#     def _group_short(self, data):
#         grouped = defaultdict(lambda: {
#             'date': None, 'gross': 0.0, 'trade_disc': 0.0, 'net_total': 0.0,
#             'add_disc': 0.0, 'add_cost': 0.0, 'round_off': 0.0,
#             'adj_amount': 0.0, 'tax_amount': 0.0, 'grand_total': 0.0,
#         })
#         for line in data:
#             key = line['date']
#             g = grouped[key]
#             if g['date'] is None:
#                 g['date'] = line['date']
#             g['gross'] += line.get('gross', 0)
#             g['trade_disc'] += line.get('trade_disc', 0)
#             g['net_total'] += line.get('net_total', 0)
#             g['add_disc'] += line.get('add_disc', 0)
#             g['add_cost'] += line.get('add_cost', 0)
#             g['round_off'] += line.get('round_off', 0)
#             g['adj_amount'] += line.get('adj_amount', 0)
#             g['tax_amount'] += line.get('tax_amount', 0)
#             g['grand_total'] += line.get('grand_total', 0)
#         result = list(grouped.values())
#         result.sort(key=lambda x: x['date'])
#         return result
#
#     def _group_short_combined(self, data):
#         grouped = defaultdict(lambda: {
#             'date': None, 'type': None, 'gross': 0.0, 'trade_disc': 0.0,
#             'net_total': 0.0, 'add_disc': 0.0, 'add_cost': 0.0, 'round_off': 0.0,
#             'adj_amount': 0.0, 'tax_amount': 0.0, 'grand_total': 0.0,
#         })
#         for line in data:
#             key = (line['date'], line.get('type', 'Sales'))
#             g = grouped[key]
#             if g['date'] is None:
#                 g['date'] = line['date']
#                 g['type'] = line.get('type', 'Sales')
#             g['gross'] += line.get('gross', 0)
#             g['trade_disc'] += line.get('trade_disc', 0)
#             g['net_total'] += line.get('net_total', 0)
#             g['add_disc'] += line.get('add_disc', 0)
#             g['add_cost'] += line.get('add_cost', 0)
#             g['round_off'] += line.get('round_off', 0)
#             g['adj_amount'] += line.get('adj_amount', 0)
#             g['tax_amount'] += line.get('tax_amount', 0)
#             g['grand_total'] += line.get('grand_total', 0)
#         result = list(grouped.values())
#         result.sort(key=lambda x: (x['date'], x['type']))
#         return result
#
#     def _get_sales_data(self):
#         self.ensure_one()
#         domain = [
#             ('invoice_date', '>=', self.date_from),
#             ('invoice_date', '<=', self.date_to),
#             ('state', '=', 'posted'),
#             ('move_type', '=', 'out_invoice'),
#             ('company_id', '=', self.company_id.id),
#         ]
#         if self.partner_ids:
#             domain.append(('partner_id', 'in', self.partner_ids.ids))
#         invoices = self.env['account.move'].search(domain, order='invoice_date asc')
#         data = []
#         for inv in invoices:
#             gross = sum(inv.invoice_line_ids.mapped('price_subtotal'))
#             trade_disc = sum((l.price_unit * l.quantity * l.discount) / 100
#                            for l in inv.invoice_line_ids if l.discount)
#             net_total = gross - trade_disc
#             tax = sum((l.price_total - l.price_subtotal) for l in inv.invoice_line_ids)
#             grand = net_total + tax
#             data.append({
#                 'date': inv.invoice_date,
#                 'customer': inv.partner_id.name,
#                 'invoice_ref': inv.ref or inv.name,
#                 'gross': gross, 'trade_disc': trade_disc, 'net_total': net_total,
#                 'add_disc': 0, 'add_cost': 0, 'round_off': 0, 'adj_amount': 0,
#                 'tax_amount': tax, 'grand_total': grand, 'type': 'Sales',
#             })
#         if self.view_type == 'short':
#             return self._group_short(data)
#         return data
#
#     def _get_return_data(self):
#         self.ensure_one()
#         domain = [
#             ('invoice_date', '>=', self.date_from),
#             ('invoice_date', '<=', self.date_to),
#             ('state', '=', 'posted'),
#             ('move_type', '=', 'out_refund'),
#             ('company_id', '=', self.company_id.id),
#         ]
#         if self.partner_ids:
#             domain.append(('partner_id', 'in', self.partner_ids.ids))
#         invoices = self.env['account.move'].search(domain, order='invoice_date asc')
#         data = []
#         for inv in invoices:
#             gross = sum(inv.invoice_line_ids.mapped('price_subtotal'))
#             trade_disc = sum((l.price_unit * l.quantity * l.discount) / 100
#                            for l in inv.invoice_line_ids if l.discount)
#             net_total = gross - trade_disc
#             tax = sum((l.price_total - l.price_subtotal) for l in inv.invoice_line_ids)
#             grand = net_total + tax
#             data.append({
#                 'date': inv.invoice_date,
#                 'customer': inv.partner_id.name,
#                 'invoice_ref': inv.ref or inv.name,
#                 'gross': -abs(gross), 'trade_disc': -abs(trade_disc),
#                 'net_total': -abs(net_total), 'add_disc': 0, 'add_cost': 0,
#                 'round_off': 0, 'adj_amount': 0, 'tax_amount': -abs(tax),
#                 'grand_total': -abs(grand), 'type': 'Return',
#             })
#         if self.view_type == 'short':
#             return self._group_short(data)
#         return data
#
#     def _get_combined_data(self):
#         original = self.view_type
#         self.view_type = 'detail'
#         sales = self._get_sales_data()
#         returns = self._get_return_data()
#         self.view_type = original
#         combined = sales + returns
#         combined.sort(key=lambda x: x['date'])
#         if original == 'short':
#             return self._group_short_combined(combined)
#         return combined
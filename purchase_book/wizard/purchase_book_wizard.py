# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime
from collections import defaultdict


class PurchaseBookWizard(models.TransientModel):
    _name = 'purchase.book.wizard'
    _description = 'Purchase Book Report Wizard'

    report_type = fields.Selection([
        ('purchase', 'Purchase Report'),
        ('return', 'Purchase Return Report'),
        ('both', 'Purchase & Purchase Return Report')
    ], string='Report Type', required=True, default='purchase')

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

    partner_ids = fields.Many2many('res.partner', string='Vendors')

    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        string='Analytic Accounts',
        help='Filter by Analytic Accounts'
    )

    include_expense = fields.Boolean(string='Include Expense Purchases', default=True)

    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)

    preview_line_ids = fields.One2many('purchase.book.preview', 'wizard_id', string='Preview Lines')

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
        return self.env.ref('purchase_book.action_report_purchase_book').report_action(self)

    def action_preview(self):
        """Generate preview data and show in tree view"""
        self.ensure_one()

        # Clear existing preview lines
        self.preview_line_ids.unlink()

        # Get report data
        data = self._get_report_data()

        # Create preview lines
        sequence = 1
        preview_vals = []

        if self.view_type == 'detail':
            # Detail view with date subtotals
            current_date = None
            date_totals = {
                'gross': 0, 'trade_disc': 0, 'net_total': 0,
                'add_disc': 0, 'add_cost': 0, 'round_off': 0,
                'adj_amount': 0, 'tax_amount': 0, 'grand_total': 0
            }

            for line in data:
                # Check if date changed - add subtotal
                if current_date and current_date != line['date']:
                    preview_vals.append({
                        'wizard_id': self.id,
                        'sequence': sequence,
                        'date': current_date,
                        'is_subtotal': True,
                        'subtotal_label': 'Total:',
                        'gross': date_totals['gross'],
                        'trade_disc': date_totals['trade_disc'],
                        'net_total': date_totals['net_total'],
                        'add_disc': date_totals['add_disc'],
                        'add_cost': date_totals['add_cost'],
                        'round_off': date_totals['round_off'],
                        'adj_amount': date_totals['adj_amount'],
                        'tax_amount': date_totals['tax_amount'],
                        'grand_total': date_totals['grand_total'],
                    })
                    sequence += 1

                    # Reset date totals
                    date_totals = {k: 0 for k in date_totals}

                # Add detail line
                preview_vals.append({
                    'wizard_id': self.id,
                    'sequence': sequence,
                    'date': line['date'],
                    'transaction_type': line.get('type', ''),
                    'vendor': line.get('vendor', ''),
                    'invoice_ref': line.get('invoice_ref', ''),
                    'gross': line['gross'],
                    'trade_disc': line['trade_disc'],
                    'net_total': line['net_total'],
                    'add_disc': line.get('add_disc', 0),
                    'add_cost': line.get('add_cost', 0),
                    'round_off': line.get('round_off', 0),
                    'adj_amount': line.get('adj_amount', 0),
                    'tax_amount': line['tax_amount'],
                    'grand_total': line['grand_total'],
                    'is_subtotal': False,
                })
                sequence += 1

                current_date = line['date']
                # Accumulate date totals
                for key in date_totals:
                    date_totals[key] += line.get(key, 0)

            # Add last date subtotal
            if current_date:
                preview_vals.append({
                    'wizard_id': self.id,
                    'sequence': sequence,
                    'date': current_date,
                    'is_subtotal': True,
                    'subtotal_label': 'Total:',
                    'gross': date_totals['gross'],
                    'trade_disc': date_totals['trade_disc'],
                    'net_total': date_totals['net_total'],
                    'add_disc': date_totals['add_disc'],
                    'add_cost': date_totals['add_cost'],
                    'round_off': date_totals['round_off'],
                    'adj_amount': date_totals['adj_amount'],
                    'tax_amount': date_totals['tax_amount'],
                    'grand_total': date_totals['grand_total'],
                })
        else:
            # Short view - simple lines
            for line in data:
                preview_vals.append({
                    'wizard_id': self.id,
                    'sequence': sequence,
                    'date': line['date'],
                    'transaction_type': line.get('type', ''),
                    'gross': line['gross'],
                    'trade_disc': line['trade_disc'],
                    'net_total': line['net_total'],
                    'add_disc': line.get('add_disc', 0),
                    'add_cost': line.get('add_cost', 0),
                    'round_off': line.get('round_off', 0),
                    'adj_amount': line.get('adj_amount', 0),
                    'tax_amount': line['tax_amount'],
                    'grand_total': line['grand_total'],
                    'is_subtotal': False,
                })
                sequence += 1

        # Create preview lines
        self.env['purchase.book.preview'].create(preview_vals)

        # Return action to show preview
        return {
            'name': 'Purchase Book Preview',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.book.preview',
            'view_mode': 'tree',
            'view_id': self.env.ref('purchase_book.view_purchase_book_preview_tree').id,
            'domain': [('wizard_id', '=', self.id)],
            'context': {
                'default_wizard_id': self.id,
                'view_type': self.view_type,
                'report_type': self.report_type,
            },
            'target': 'new',
        }

    def _get_report_data(self):
        self.ensure_one()

        if self.report_type == 'purchase':
            return self._get_purchase_data()
        elif self.report_type == 'return':
            return self._get_return_data()
        else:
            return self._get_combined_data()

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
            key = (line['date'], line.get('type', 'Purchase'))
            g = grouped[key]

            if g['date'] is None:
                g['date'] = line['date']
                g['type'] = line.get('type', 'Purchase')

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

    def _get_purchase_data(self):
        self.ensure_one()

        domain = [
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
            ('state', '=', 'posted'),
            ('move_type', '=', 'in_invoice'),
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
                'vendor': inv.partner_id.name,
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
                'type': 'Purchase',
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
            ('move_type', '=', 'in_refund'),
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
                'vendor': inv.partner_id.name,
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

    def _get_combined_data(self):
        original = self.view_type
        self.view_type = 'detail'

        purchase = self._get_purchase_data()
        returns = self._get_return_data()

        self.view_type = original

        combined = purchase + returns
        combined.sort(key=lambda x: x['date'])

        if original == 'short':
            return self._group_short_combined(combined)

        return combined

    def _get_report_values(self):
        return {
            'doc_ids': self.ids,
            'doc_model': 'purchase.book.wizard',
            'docs': self,
            'data': self._get_report_data(),
            'date_from': self.date_from,
            'date_to': self.date_to,
            'report_type': self.report_type,
            'company': self.company_id,
            'analytic_accounts': self.analytic_account_ids,
        }













# from odoo import models, fields, api
# from datetime import datetime
# from collections import defaultdict
#
#
# class PurchaseBookWizard(models.TransientModel):
#     _name = 'purchase.book.wizard'
#     _description = 'Purchase Book Report Wizard'
#
#     report_type = fields.Selection([
#         ('purchase', 'Purchase Report'),
#         ('return', 'Purchase Return Report'),
#         ('both', 'Purchase & Purchase Return Report')
#     ], string='Report Type', required=True, default='purchase')
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
#     partner_ids = fields.Many2many('res.partner', string='Vendors')
#
#     analytic_account_ids = fields.Many2many(
#         'account.analytic.account',
#         string='Analytic Accounts',
#         help='Filter by Analytic Accounts'
#     )
#
#     include_expense = fields.Boolean(string='Include Expense Purchases', default=True)
#
#     company_id = fields.Many2one('res.company', string='Company',
#                                  default=lambda self: self.env.company)
#
#     # -------------------------------------------------------------
#     # DATE FILTER
#     # -------------------------------------------------------------
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
#     # -------------------------------------------------------------
#     # MAIN ENTRY
#     # -------------------------------------------------------------
#     def action_print_report(self):
#         self.ensure_one()
#         return self.env.ref('purchase_book.action_report_purchase_book').report_action(self)
#
#     def _get_report_data(self):
#         self.ensure_one()
#
#         if self.report_type == 'purchase':
#             return self._get_purchase_data()
#
#         elif self.report_type == 'return':
#             return self._get_return_data()
#
#         else:
#             return self._get_combined_data()
#
#     # -------------------------------------------------------------
#     # GROUPING FUNCTION (SHORT VIEW)
#     # -------------------------------------------------------------
#     def _group_short(self, data):
#         """Group data by date (short view)."""
#         grouped = defaultdict(lambda: {
#             'date': None,
#             'gross': 0.0,
#             'trade_disc': 0.0,
#             'net_total': 0.0,
#             'add_disc': 0.0,
#             'add_cost': 0.0,
#             'round_off': 0.0,
#             'adj_amount': 0.0,
#             'tax_amount': 0.0,
#             'grand_total': 0.0,
#         })
#
#         for line in data:
#             key = line['date']
#             g = grouped[key]
#
#             if g['date'] is None:
#                 g['date'] = line['date']
#
#             g['gross'] += line.get('gross', 0)
#             g['trade_disc'] += line.get('trade_disc', 0)
#             g['net_total'] += line.get('net_total', 0)
#             g['add_disc'] += line.get('add_disc', 0)
#             g['add_cost'] += line.get('add_cost', 0)
#             g['round_off'] += line.get('round_off', 0)
#             g['adj_amount'] += line.get('adj_amount', 0)
#             g['tax_amount'] += line.get('tax_amount', 0)
#             g['grand_total'] += line.get('grand_total', 0)
#
#         result = list(grouped.values())
#         result.sort(key=lambda x: x['date'])
#         return result
#
#     def _group_short_combined(self, data):
#         """Group combined data by date and type for short view."""
#         grouped = defaultdict(lambda: {
#             'date': None,
#             'type': None,
#             'gross': 0.0,
#             'trade_disc': 0.0,
#             'net_total': 0.0,
#             'add_disc': 0.0,
#             'add_cost': 0.0,
#             'round_off': 0.0,
#             'adj_amount': 0.0,
#             'tax_amount': 0.0,
#             'grand_total': 0.0,
#         })
#
#         for line in data:
#             # Key is date + type
#             key = (line['date'], line.get('type', 'Purchase'))
#             g = grouped[key]
#
#             if g['date'] is None:
#                 g['date'] = line['date']
#                 g['type'] = line.get('type', 'Purchase')
#
#             g['gross'] += line.get('gross', 0)
#             g['trade_disc'] += line.get('trade_disc', 0)
#             g['net_total'] += line.get('net_total', 0)
#             g['add_disc'] += line.get('add_disc', 0)
#             g['add_cost'] += line.get('add_cost', 0)
#             g['round_off'] += line.get('round_off', 0)
#             g['adj_amount'] += line.get('adj_amount', 0)
#             g['tax_amount'] += line.get('tax_amount', 0)
#             g['grand_total'] += line.get('grand_total', 0)
#
#         result = list(grouped.values())
#         result.sort(key=lambda x: (x['date'], x['type']))
#         return result
#
#     # -------------------------------------------------------------
#     # PURCHASE DATA
#     # -------------------------------------------------------------
#     def _get_purchase_data(self):
#         self.ensure_one()
#
#         domain = [
#             ('invoice_date', '>=', self.date_from),
#             ('invoice_date', '<=', self.date_to),
#             ('state', '=', 'posted'),
#             ('move_type', '=', 'in_invoice'),
#             ('company_id', '=', self.company_id.id),
#         ]
#
#         if self.partner_ids:
#             domain.append(('partner_id', 'in', self.partner_ids.ids))
#
#         invoices = self.env['account.move'].search(domain, order='invoice_date asc')
#
#         data = []
#         for inv in invoices:
#             gross = sum(inv.invoice_line_ids.mapped('price_subtotal'))
#             trade_disc = 0
#             for l in inv.invoice_line_ids:
#                 if l.discount:
#                     trade_disc += (l.price_unit * l.quantity * l.discount) / 100
#
#             net_total = gross - trade_disc
#             tax = sum((l.price_total - l.price_subtotal) for l in inv.invoice_line_ids)
#             grand = net_total + tax
#
#             data.append({
#                 'date': inv.invoice_date,
#                 'vendor': inv.partner_id.name,
#                 'invoice_ref': inv.ref or inv.name,
#                 'gross': gross,
#                 'trade_disc': trade_disc,
#                 'net_total': net_total,
#                 'add_disc': 0,
#                 'add_cost': 0,
#                 'round_off': 0,
#                 'adj_amount': 0,
#                 'tax_amount': tax,
#                 'grand_total': grand,
#                 'type': 'Purchase',  # Added type field
#             })
#
#         if self.view_type == 'short':
#             return self._group_short(data)
#
#         return data
#
#     # -------------------------------------------------------------
#     # RETURN DATA
#     # -------------------------------------------------------------
#     def _get_return_data(self):
#         self.ensure_one()
#
#         domain = [
#             ('invoice_date', '>=', self.date_from),
#             ('invoice_date', '<=', self.date_to),
#             ('state', '=', 'posted'),
#             ('move_type', '=', 'in_refund'),
#             ('company_id', '=', self.company_id.id),
#         ]
#
#         if self.partner_ids:
#             domain.append(('partner_id', 'in', self.partner_ids.ids))
#
#         invoices = self.env['account.move'].search(domain, order='invoice_date asc')
#
#         data = []
#         for inv in invoices:
#             gross = sum(inv.invoice_line_ids.mapped('price_subtotal'))
#             trade_disc = 0
#             for l in inv.invoice_line_ids:
#                 if l.discount:
#                     trade_disc += (l.price_unit * l.quantity * l.discount) / 100
#
#             net_total = gross - trade_disc
#             tax = sum((l.price_total - l.price_subtotal) for l in inv.invoice_line_ids)
#             grand = net_total + tax
#
#             # Return should be NEGATIVE
#             data.append({
#                 'date': inv.invoice_date,
#                 'vendor': inv.partner_id.name,
#                 'invoice_ref': inv.ref or inv.name,
#                 'gross': -abs(gross),
#                 'trade_disc': -abs(trade_disc),
#                 'net_total': -abs(net_total),
#                 'add_disc': 0,
#                 'add_cost': 0,
#                 'round_off': 0,
#                 'adj_amount': 0,
#                 'tax_amount': -abs(tax),
#                 'grand_total': -abs(grand),
#                 'type': 'Return',  # Added type field
#             })
#
#         if self.view_type == 'short':
#             return self._group_short(data)
#
#         return data
#
#     # -------------------------------------------------------------
#     # COMBINED DATA (PURCHASE + RETURN)
#     # -------------------------------------------------------------
#     def _get_combined_data(self):
#         # temporarily force detail
#         original = self.view_type
#         self.view_type = 'detail'
#
#         purchase = self._get_purchase_data()
#         returns = self._get_return_data()
#
#         self.view_type = original  # restore
#
#         combined = purchase + returns
#         combined.sort(key=lambda x: x['date'])
#
#         if original == 'short':
#             return self._group_short_combined(combined)
#
#         return combined
#
#     # -------------------------------------------------------------
#     # REPORT VALUES
#     # -------------------------------------------------------------
#     def _get_report_values(self):
#         return {
#             'doc_ids': self.ids,
#             'doc_model': 'purchase.book.wizard',
#             'docs': self,
#             'data': self._get_report_data(),
#             'date_from': self.date_from,
#             'date_to': self.date_to,
#             'report_type': self.report_type,
#             'company': self.company_id,
#             'analytic_accounts': self.analytic_account_ids,
#         }
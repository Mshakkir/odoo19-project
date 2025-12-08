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
        return self.env.ref('purchase_book.action_report_purchase_book').report_action(self)

    def _get_report_data(self):
        self.ensure_one()

        if self.report_type == 'purchase':
            return self._get_purchase_data()

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

    # -------------------------------------------------------------
    # PURCHASE DATA
    # -------------------------------------------------------------
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

            # Return should be NEGATIVE
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
            })

        if self.view_type == 'short':
            return self._group_short(data)

        return data

    # -------------------------------------------------------------
    # COMBINED DATA (PURCHASE + RETURN)
    # -------------------------------------------------------------
    def _get_combined_data(self):
        # temporarily force detail
        original = self.view_type
        self.view_type = 'detail'

        purchase = self._get_purchase_data()
        returns = self._get_return_data()

        self.view_type = original  # restore

        combined = purchase + returns
        combined.sort(key=lambda x: x['date'])

        if original == 'short':
            return self._group_short(combined)

        return combined

    # -------------------------------------------------------------
    # REPORT VALUES
    # -------------------------------------------------------------
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
#         help='Filter by Analytic Accounts (Cost Centers/Projects)'
#     )
#
#     include_expense = fields.Boolean(string='Include Expense Purchases', default=True)
#
#     company_id = fields.Many2one('res.company', string='Company',
#                                  default=lambda self: self.env.company)
#
#     @api.onchange('filter_type')
#     def _onchange_filter_type(self):
#         """Auto-set date range based on filter type"""
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
#         """Generate the selected report"""
#         self.ensure_one()
#         return self.env.ref('purchase_book.action_report_purchase_book').report_action(self)
#
#     def _get_report_data(self):
#         """Get report data based on report type"""
#         self.ensure_one()
#
#         if self.report_type == 'purchase':
#             return self._get_purchase_data()
#         elif self.report_type == 'return':
#             return self._get_return_data()
#         else:  # both
#             return self._get_combined_data()
#
#     def _get_purchase_data(self):
#         """Fetch purchase order data based on filters with analytic accounts"""
#         self.ensure_one()
#
#         # Base domain for posted vendor bills
#         domain = [
#             ('invoice_date', '>=', self.date_from),
#             ('invoice_date', '<=', self.date_to),
#             ('state', '=', 'posted'),
#             ('move_type', '=', 'in_invoice'),
#             ('company_id', '=', self.company_id.id)
#         ]
#
#         if self.partner_ids:
#             domain.append(('partner_id', 'in', self.partner_ids.ids))
#
#         # If analytic accounts are selected, filter invoice lines by analytic account
#         if self.analytic_account_ids:
#             # Find invoices that have lines with selected analytic accounts
#             invoice_lines = self.env['account.move.line'].search([
#                 ('analytic_distribution', '!=', False),
#                 ('parent_state', '=', 'posted'),
#                 ('move_id.move_type', '=', 'in_invoice'),
#                 ('move_id.invoice_date', '>=', self.date_from),
#                 ('move_id.invoice_date', '<=', self.date_to),
#             ])
#
#             # Filter lines by analytic accounts (checking analytic_distribution JSON field)
#             filtered_invoice_ids = set()
#             for line in invoice_lines:
#                 if line.analytic_distribution:
#                     # analytic_distribution is stored as JSON: {analytic_account_id: percentage}
#                     analytic_ids = [int(aid) for aid in line.analytic_distribution.keys()]
#                     if any(aid in self.analytic_account_ids.ids for aid in analytic_ids):
#                         filtered_invoice_ids.add(line.move_id.id)
#
#             if filtered_invoice_ids:
#                 domain.append(('id', 'in', list(filtered_invoice_ids)))
#             else:
#                 # No invoices found with selected analytic accounts
#                 return []
#
#         invoices = self.env['account.move'].search(domain, order='invoice_date asc, name asc')
#
#         data = []
#         for invoice in invoices:
#             # If analytic filter is active, only sum lines with matching analytic accounts
#             if self.analytic_account_ids:
#                 relevant_lines = invoice.invoice_line_ids.filtered(
#                     lambda l: l.analytic_distribution and any(
#                         int(aid) in self.analytic_account_ids.ids
#                         for aid in l.analytic_distribution.keys()
#                     )
#                 )
#             else:
#                 relevant_lines = invoice.invoice_line_ids
#
#             if not relevant_lines:
#                 continue
#
#             # Calculate amounts from relevant lines only
#             gross_total = sum(line.price_subtotal for line in relevant_lines)
#             trade_disc = 0.0
#             for line in relevant_lines:
#                 if line.discount:
#                     discount_amount = (line.price_unit * line.quantity * line.discount) / 100
#                     trade_disc += discount_amount
#
#             net_total = gross_total - trade_disc
#             tax_amount = sum((line.price_total - line.price_subtotal) for line in relevant_lines)
#             grand_total = net_total + tax_amount
#
#             # Get analytic account names
#             analytic_names = []
#             if self.analytic_account_ids:
#                 for line in relevant_lines:
#                     if line.analytic_distribution:
#                         for aid in line.analytic_distribution.keys():
#                             analytic = self.env['account.analytic.account'].browse(int(aid))
#                             if analytic.name not in analytic_names:
#                                 analytic_names.append(analytic.name)
#
#             data.append({
#                 'date': invoice.invoice_date,
#                 'vendor': invoice.partner_id.name,
#                 'invoice_ref': invoice.ref or invoice.name,
#                 'po_number': ', '.join(relevant_lines.mapped('purchase_line_id.order_id.name')) or '',
#                 'analytic_account': ', '.join(analytic_names) if analytic_names else '',
#                 'gross': gross_total,
#                 'trade_disc': trade_disc,
#                 'net_total': net_total,
#                 'add_disc': 0.0,
#                 'add_cost': 0.0,
#                 'round_off': 0.0,
#                 'adj_amount': 0.0,
#                 'tax_amount': tax_amount,
#                 'grand_total': grand_total,
#             })
#
#         return data
#
#     def _get_return_data(self):
#         """Fetch purchase return (refund) data based on filters with analytic accounts"""
#         self.ensure_one()
#
#         domain = [
#             ('invoice_date', '>=', self.date_from),
#             ('invoice_date', '<=', self.date_to),
#             ('state', '=', 'posted'),
#             ('move_type', '=', 'in_refund'),
#             ('company_id', '=', self.company_id.id)
#         ]
#
#         if self.partner_ids:
#             domain.append(('partner_id', 'in', self.partner_ids.ids))
#
#         # Filter by analytic accounts if selected
#         if self.analytic_account_ids:
#             invoice_lines = self.env['account.move.line'].search([
#                 ('analytic_distribution', '!=', False),
#                 ('parent_state', '=', 'posted'),
#                 ('move_id.move_type', '=', 'in_refund'),
#                 ('move_id.invoice_date', '>=', self.date_from),
#                 ('move_id.invoice_date', '<=', self.date_to),
#             ])
#
#             filtered_invoice_ids = set()
#             for line in invoice_lines:
#                 if line.analytic_distribution:
#                     analytic_ids = [int(aid) for aid in line.analytic_distribution.keys()]
#                     if any(aid in self.analytic_account_ids.ids for aid in analytic_ids):
#                         filtered_invoice_ids.add(line.move_id.id)
#
#             if filtered_invoice_ids:
#                 domain.append(('id', 'in', list(filtered_invoice_ids)))
#             else:
#                 return []
#
#         refunds = self.env['account.move'].search(domain, order='invoice_date asc, name asc')
#
#         data = []
#         for refund in refunds:
#             # Filter lines by analytic accounts
#             if self.analytic_account_ids:
#                 relevant_lines = refund.invoice_line_ids.filtered(
#                     lambda l: l.analytic_distribution and any(
#                         int(aid) in self.analytic_account_ids.ids
#                         for aid in l.analytic_distribution.keys()
#                     )
#                 )
#             else:
#                 relevant_lines = refund.invoice_line_ids
#
#             if not relevant_lines:
#                 continue
#
#             gross_total = sum(line.price_subtotal for line in relevant_lines)
#             trade_disc = 0.0
#             for line in relevant_lines:
#                 if line.discount:
#                     discount_amount = (line.price_unit * line.quantity * line.discount) / 100
#                     trade_disc += discount_amount
#
#             net_total = gross_total - trade_disc
#             tax_amount = sum((line.price_total - line.price_subtotal) for line in relevant_lines)
#             grand_total = net_total + tax_amount
#
#             data.append({
#                 'date': refund.invoice_date,
#                 'vendor': refund.partner_id.name,
#                 'invoice_ref': refund.ref or refund.name,
#                 'gross': gross_total,
#                 'trade_disc': trade_disc,
#                 'net_total': net_total,
#                 'add_disc': 0.0,
#                 'add_cost': 0.0,
#                 'round_off': 0.0,
#                 'adj_amount': 0.0,
#                 'tax_amount': tax_amount,
#                 'grand_total': grand_total,
#             })
#
#         # For short view, group by date
#         if self.view_type == 'short':
#             return self._group_data_by_date(data)
#
#         return data
#
#     def _get_combined_data(self):
#         """Fetch both purchase and return data with analytic filtering"""
#         self.ensure_one()
#
#         # Temporarily set view_type to detail to get individual records
#         original_view = self.view_type
#         self.view_type = 'detail'
#
#         purchase_data = self._get_purchase_data()
#         return_data = self._get_return_data()
#
#         # Restore original view type
#         self.view_type = original_view
#
#         # Mark transaction types
#         for item in purchase_data:
#             item['type'] = 'Purchase'
#             item['type_label'] = 'Purchase Invoice'
#
#         for item in return_data:
#             item['type'] = 'Return'
#             item['type_label'] = 'Purchase Return'
#             # Make return values negative for proper accounting
#             item['gross'] = -abs(item['gross'])
#             item['net_total'] = -abs(item['net_total'])
#             item['tax_amount'] = -abs(item['tax_amount'])
#             item['grand_total'] = -abs(item['grand_total'])
#
#         # Combine and sort by date
#         combined = purchase_data + return_data
#         combined.sort(key=lambda x: x['date'])
#
#         # For short view, group by date and type
#         if original_view == 'short':
#             return self._group_combined_data_by_date_type(combined)
#
#         return combined
#
#     def _group_combined_data_by_date_type(self, data):
#         """Group combined data by date and type for short view"""
#         from collections import defaultdict
#         grouped = defaultdict(lambda: {
#             'date': None,
#             'type': None,
#             'gross': 0,
#             'trade_disc': 0,
#             'net_total': 0,
#             'tax_amount': 0,
#             'add_cost': 0,
#             'adj_amount': 0,
#             'grand_total': 0
#         })
#
#         for line in data:
#             key = (line['date'], line['type'])
#             if grouped[key]['date'] is None:
#                 grouped[key]['date'] = line['date']
#                 grouped[key]['type'] = line['type']
#
#             grouped[key]['gross'] += line['gross']
#             grouped[key]['trade_disc'] += line['trade_disc']
#             grouped[key]['net_total'] += line['net_total']
#             grouped[key]['tax_amount'] += line['tax_amount']
#             grouped[key]['add_cost'] += line['add_cost']
#             grouped[key]['adj_amount'] += line['adj_amount']
#             grouped[key]['grand_total'] += line['grand_total']
#
#         # Convert to list and sort by date then type
#         result = list(grouped.values())
#         result.sort(key=lambda x: (x['date'], x['type']))
#         return result
#
#     def _get_report_values(self):
#         """Get values to pass to the report template"""
#         self.ensure_one()
#
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














# from odoo import models, fields, api
# from datetime import datetime
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
#         help='Filter by Analytic Accounts (Cost Centers/Projects)'
#     )
#
#     include_expense = fields.Boolean(string='Include Expense Purchases', default=True)
#
#     company_id = fields.Many2one('res.company', string='Company',
#                                  default=lambda self: self.env.company)
#
#     @api.onchange('filter_type')
#     def _onchange_filter_type(self):
#         """Auto-set date range based on filter type"""
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
#         """Generate the selected report"""
#         self.ensure_one()
#         return self.env.ref('purchase_book.action_report_purchase_book').report_action(self)
#
#     def _get_report_data(self):
#         """Get report data based on report type"""
#         self.ensure_one()
#
#         if self.report_type == 'purchase':
#             return self._get_purchase_data()
#         elif self.report_type == 'return':
#             return self._get_return_data()
#         else:  # both
#             return self._get_combined_data()
#
#     def _get_purchase_data(self):
#         """Fetch purchase order data based on filters with analytic accounts"""
#         self.ensure_one()
#
#         # Base domain for posted vendor bills
#         domain = [
#             ('invoice_date', '>=', self.date_from),
#             ('invoice_date', '<=', self.date_to),
#             ('state', '=', 'posted'),
#             ('move_type', '=', 'in_invoice'),
#             ('company_id', '=', self.company_id.id)
#         ]
#
#         if self.partner_ids:
#             domain.append(('partner_id', 'in', self.partner_ids.ids))
#
#         # If analytic accounts are selected, filter invoice lines by analytic account
#         if self.analytic_account_ids:
#             # Find invoices that have lines with selected analytic accounts
#             invoice_lines = self.env['account.move.line'].search([
#                 ('analytic_distribution', '!=', False),
#                 ('parent_state', '=', 'posted'),
#                 ('move_id.move_type', '=', 'in_invoice'),
#                 ('move_id.invoice_date', '>=', self.date_from),
#                 ('move_id.invoice_date', '<=', self.date_to),
#             ])
#
#             # Filter lines by analytic accounts (checking analytic_distribution JSON field)
#             filtered_invoice_ids = set()
#             for line in invoice_lines:
#                 if line.analytic_distribution:
#                     # analytic_distribution is stored as JSON: {analytic_account_id: percentage}
#                     analytic_ids = [int(aid) for aid in line.analytic_distribution.keys()]
#                     if any(aid in self.analytic_account_ids.ids for aid in analytic_ids):
#                         filtered_invoice_ids.add(line.move_id.id)
#
#             if filtered_invoice_ids:
#                 domain.append(('id', 'in', list(filtered_invoice_ids)))
#             else:
#                 # No invoices found with selected analytic accounts
#                 return []
#
#         invoices = self.env['account.move'].search(domain, order='invoice_date asc, name asc')
#
#         data = []
#         for invoice in invoices:
#             # If analytic filter is active, only sum lines with matching analytic accounts
#             if self.analytic_account_ids:
#                 relevant_lines = invoice.invoice_line_ids.filtered(
#                     lambda l: l.analytic_distribution and any(
#                         int(aid) in self.analytic_account_ids.ids
#                         for aid in l.analytic_distribution.keys()
#                     )
#                 )
#             else:
#                 relevant_lines = invoice.invoice_line_ids
#
#             if not relevant_lines:
#                 continue
#
#             # Calculate amounts from relevant lines only
#             gross_total = sum(line.price_subtotal for line in relevant_lines)
#             trade_disc = 0.0
#             for line in relevant_lines:
#                 if line.discount:
#                     discount_amount = (line.price_unit * line.quantity * line.discount) / 100
#                     trade_disc += discount_amount
#
#             net_total = gross_total - trade_disc
#             tax_amount = sum((line.price_total - line.price_subtotal) for line in relevant_lines)
#             grand_total = net_total + tax_amount
#
#             # Get analytic account names
#             analytic_names = []
#             if self.analytic_account_ids:
#                 for line in relevant_lines:
#                     if line.analytic_distribution:
#                         for aid in line.analytic_distribution.keys():
#                             analytic = self.env['account.analytic.account'].browse(int(aid))
#                             if analytic.name not in analytic_names:
#                                 analytic_names.append(analytic.name)
#
#             data.append({
#                 'date': invoice.invoice_date,
#                 'vendor': invoice.partner_id.name,
#                 'invoice_ref': invoice.ref or invoice.name,
#                 'po_number': ', '.join(relevant_lines.mapped('purchase_line_id.order_id.name')) or '',
#                 'analytic_account': ', '.join(analytic_names) if analytic_names else '',
#                 'gross': gross_total,
#                 'trade_disc': trade_disc,
#                 'net_total': net_total,
#                 'add_disc': 0.0,
#                 'add_cost': 0.0,
#                 'round_off': 0.0,
#                 'adj_amount': 0.0,
#                 'tax_amount': tax_amount,
#                 'grand_total': grand_total,
#             })
#
#         return data
#
#     def _get_return_data(self):
#         """Fetch purchase return (refund) data based on filters with analytic accounts"""
#         self.ensure_one()
#
#         domain = [
#             ('invoice_date', '>=', self.date_from),
#             ('invoice_date', '<=', self.date_to),
#             ('state', '=', 'posted'),
#             ('move_type', '=', 'in_refund'),
#             ('company_id', '=', self.company_id.id)
#         ]
#
#         if self.partner_ids:
#             domain.append(('partner_id', 'in', self.partner_ids.ids))
#
#         # Filter by analytic accounts if selected
#         if self.analytic_account_ids:
#             invoice_lines = self.env['account.move.line'].search([
#                 ('analytic_distribution', '!=', False),
#                 ('parent_state', '=', 'posted'),
#                 ('move_id.move_type', '=', 'in_refund'),
#                 ('move_id.invoice_date', '>=', self.date_from),
#                 ('move_id.invoice_date', '<=', self.date_to),
#             ])
#
#             filtered_invoice_ids = set()
#             for line in invoice_lines:
#                 if line.analytic_distribution:
#                     analytic_ids = [int(aid) for aid in line.analytic_distribution.keys()]
#                     if any(aid in self.analytic_account_ids.ids for aid in analytic_ids):
#                         filtered_invoice_ids.add(line.move_id.id)
#
#             if filtered_invoice_ids:
#                 domain.append(('id', 'in', list(filtered_invoice_ids)))
#             else:
#                 return []
#
#         refunds = self.env['account.move'].search(domain, order='invoice_date asc, name asc')
#
#         data = []
#         for refund in refunds:
#             # Filter lines by analytic accounts
#             if self.analytic_account_ids:
#                 relevant_lines = refund.invoice_line_ids.filtered(
#                     lambda l: l.analytic_distribution and any(
#                         int(aid) in self.analytic_account_ids.ids
#                         for aid in l.analytic_distribution.keys()
#                     )
#                 )
#             else:
#                 relevant_lines = refund.invoice_line_ids
#
#             if not relevant_lines:
#                 continue
#
#             gross_total = sum(line.price_subtotal for line in relevant_lines)
#             trade_disc = 0.0
#             for line in relevant_lines:
#                 if line.discount:
#                     discount_amount = (line.price_unit * line.quantity * line.discount) / 100
#                     trade_disc += discount_amount
#
#             net_total = gross_total - trade_disc
#             tax_amount = sum((line.price_total - line.price_subtotal) for line in relevant_lines)
#             grand_total = net_total + tax_amount
#
#             # Get analytic account names
#             analytic_names = []
#             if self.analytic_account_ids:
#                 for line in relevant_lines:
#                     if line.analytic_distribution:
#                         for aid in line.analytic_distribution.keys():
#                             analytic = self.env['account.analytic.account'].browse(int(aid))
#                             if analytic.name not in analytic_names:
#                                 analytic_names.append(analytic.name)
#
#             data.append({
#                 'date': refund.invoice_date,
#                 'vendor': refund.partner_id.name,
#                 'invoice_ref': refund.ref or refund.name,
#                 'analytic_account': ', '.join(analytic_names) if analytic_names else '',
#                 'gross': gross_total,
#                 'trade_disc': trade_disc,
#                 'net_total': net_total,
#                 'add_disc': 0.0,
#                 'add_cost': 0.0,
#                 'round_off': 0.0,
#                 'adj_amount': 0.0,
#                 'tax_amount': tax_amount,
#                 'grand_total': grand_total,
#             })
#
#         return data
#
#     def _get_combined_data(self):
#         """Fetch both purchase and return data with analytic filtering"""
#         self.ensure_one()
#
#         purchase_data = self._get_purchase_data()
#         return_data = self._get_return_data()
#
#         # Mark transaction types
#         for item in purchase_data:
#             item['type'] = 'Purchase'
#             item['type_label'] = 'Purchase Invoice'
#
#         for item in return_data:
#             item['type'] = 'Return'
#             item['type_label'] = 'Purchase Return'
#             # Make return values negative for proper accounting
#             item['gross'] = -abs(item['gross'])
#             item['net_total'] = -abs(item['net_total'])
#             item['tax_amount'] = -abs(item['tax_amount'])
#             item['grand_total'] = -abs(item['grand_total'])
#
#         # Combine and sort by date
#         combined = purchase_data + return_data
#         combined.sort(key=lambda x: x['date'])
#
#         return combined
#
#     def _get_report_values(self):
#         """Get values to pass to the report template"""
#         self.ensure_one()
#
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
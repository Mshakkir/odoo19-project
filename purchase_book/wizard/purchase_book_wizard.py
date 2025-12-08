from odoo import models, fields, api
from datetime import datetime


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
        help='Filter by Analytic Accounts (Cost Centers/Projects)'
    )

    include_expense = fields.Boolean(string='Include Expense Purchases', default=True)

    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)

    @api.onchange('filter_type')
    def _onchange_filter_type(self):
        """Auto-set date range based on filter type"""
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
        """Generate the selected report"""
        self.ensure_one()
        return self.env.ref('purchase_book.action_report_purchase_book').report_action(self)

    def _get_report_data(self):
        """Get report data based on report type"""
        self.ensure_one()

        if self.report_type == 'purchase':
            return self._get_purchase_data()
        elif self.report_type == 'return':
            return self._get_return_data()
        else:  # both
            return self._get_combined_data()

    def _get_purchase_data(self):
        """Fetch purchase order data based on filters with analytic accounts"""
        self.ensure_one()

        # Base domain for posted vendor bills
        domain = [
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
            ('state', '=', 'posted'),
            ('move_type', '=', 'in_invoice'),
            ('company_id', '=', self.company_id.id)
        ]

        if self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))

        # If analytic accounts are selected, filter invoice lines by analytic account
        if self.analytic_account_ids:
            # Find invoices that have lines with selected analytic accounts
            invoice_lines = self.env['account.move.line'].search([
                ('analytic_distribution', '!=', False),
                ('parent_state', '=', 'posted'),
                ('move_id.move_type', '=', 'in_invoice'),
                ('move_id.invoice_date', '>=', self.date_from),
                ('move_id.invoice_date', '<=', self.date_to),
            ])

            # Filter lines by analytic accounts (checking analytic_distribution JSON field)
            filtered_invoice_ids = set()
            for line in invoice_lines:
                if line.analytic_distribution:
                    # analytic_distribution is stored as JSON: {analytic_account_id: percentage}
                    analytic_ids = [int(aid) for aid in line.analytic_distribution.keys()]
                    if any(aid in self.analytic_account_ids.ids for aid in analytic_ids):
                        filtered_invoice_ids.add(line.move_id.id)

            if filtered_invoice_ids:
                domain.append(('id', 'in', list(filtered_invoice_ids)))
            else:
                # No invoices found with selected analytic accounts
                return []

        invoices = self.env['account.move'].search(domain, order='invoice_date asc, name asc')

        data = []
        for invoice in invoices:
            # If analytic filter is active, only sum lines with matching analytic accounts
            if self.analytic_account_ids:
                relevant_lines = invoice.invoice_line_ids.filtered(
                    lambda l: l.analytic_distribution and any(
                        int(aid) in self.analytic_account_ids.ids
                        for aid in l.analytic_distribution.keys()
                    )
                )
            else:
                relevant_lines = invoice.invoice_line_ids

            if not relevant_lines:
                continue

            # Calculate amounts from relevant lines only
            gross_total = sum(line.price_subtotal for line in relevant_lines)
            trade_disc = 0.0
            for line in relevant_lines:
                if line.discount:
                    discount_amount = (line.price_unit * line.quantity * line.discount) / 100
                    trade_disc += discount_amount

            net_total = gross_total - trade_disc
            tax_amount = sum((line.price_total - line.price_subtotal) for line in relevant_lines)
            grand_total = net_total + tax_amount

            # Get analytic account names
            analytic_names = []
            if self.analytic_account_ids:
                for line in relevant_lines:
                    if line.analytic_distribution:
                        for aid in line.analytic_distribution.keys():
                            analytic = self.env['account.analytic.account'].browse(int(aid))
                            if analytic.name not in analytic_names:
                                analytic_names.append(analytic.name)

            data.append({
                'date': invoice.invoice_date,
                'vendor': invoice.partner_id.name,
                'invoice_ref': invoice.ref or invoice.name,
                'po_number': ', '.join(relevant_lines.mapped('purchase_line_id.order_id.name')) or '',
                'analytic_account': ', '.join(analytic_names) if analytic_names else '',
                'gross': gross_total,
                'trade_disc': trade_disc,
                'net_total': net_total,
                'add_disc': 0.0,
                'add_cost': 0.0,
                'round_off': 0.0,
                'adj_amount': 0.0,
                'tax_amount': tax_amount,
                'grand_total': grand_total,
            })

        return data

    def _get_return_data(self):
        """Fetch purchase return (refund) data based on filters with analytic accounts"""
        self.ensure_one()

        domain = [
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
            ('state', '=', 'posted'),
            ('move_type', '=', 'in_refund'),
            ('company_id', '=', self.company_id.id)
        ]

        if self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))

        # Filter by analytic accounts if selected
        if self.analytic_account_ids:
            invoice_lines = self.env['account.move.line'].search([
                ('analytic_distribution', '!=', False),
                ('parent_state', '=', 'posted'),
                ('move_id.move_type', '=', 'in_refund'),
                ('move_id.invoice_date', '>=', self.date_from),
                ('move_id.invoice_date', '<=', self.date_to),
            ])

            filtered_invoice_ids = set()
            for line in invoice_lines:
                if line.analytic_distribution:
                    analytic_ids = [int(aid) for aid in line.analytic_distribution.keys()]
                    if any(aid in self.analytic_account_ids.ids for aid in analytic_ids):
                        filtered_invoice_ids.add(line.move_id.id)

            if filtered_invoice_ids:
                domain.append(('id', 'in', list(filtered_invoice_ids)))
            else:
                return []

        refunds = self.env['account.move'].search(domain, order='invoice_date asc, name asc')

        data = []
        for refund in refunds:
            # Filter lines by analytic accounts
            if self.analytic_account_ids:
                relevant_lines = refund.invoice_line_ids.filtered(
                    lambda l: l.analytic_distribution and any(
                        int(aid) in self.analytic_account_ids.ids
                        for aid in l.analytic_distribution.keys()
                    )
                )
            else:
                relevant_lines = refund.invoice_line_ids

            if not relevant_lines:
                continue

            gross_total = sum(line.price_subtotal for line in relevant_lines)
            trade_disc = 0.0
            for line in relevant_lines:
                if line.discount:
                    discount_amount = (line.price_unit * line.quantity * line.discount) / 100
                    trade_disc += discount_amount

            net_total = gross_total - trade_disc
            tax_amount = sum((line.price_total - line.price_subtotal) for line in relevant_lines)
            grand_total = net_total + tax_amount

            # Get analytic account names
            analytic_names = []
            if self.analytic_account_ids:
                for line in relevant_lines:
                    if line.analytic_distribution:
                        for aid in line.analytic_distribution.keys():
                            analytic = self.env['account.analytic.account'].browse(int(aid))
                            if analytic.name not in analytic_names:
                                analytic_names.append(analytic.name)

            data.append({
                'date': refund.invoice_date,
                'vendor': refund.partner_id.name,
                'invoice_ref': refund.ref or refund.name,
                'analytic_account': ', '.join(analytic_names) if analytic_names else '',
                'gross': gross_total,
                'trade_disc': trade_disc,
                'net_total': net_total,
                'add_disc': 0.0,
                'add_cost': 0.0,
                'round_off': 0.0,
                'adj_amount': 0.0,
                'tax_amount': tax_amount,
                'grand_total': grand_total,
            })

        return data

    def _get_combined_data(self):
        """Fetch both purchase and return data with analytic filtering"""
        self.ensure_one()

        purchase_data = self._get_purchase_data()
        return_data = self._get_return_data()

        # Mark transaction types
        for item in purchase_data:
            item['type'] = 'Purchase'
            item['type_label'] = 'Purchase Invoice'

        for item in return_data:
            item['type'] = 'Return'
            item['type_label'] = 'Purchase Return'
            # Make return values negative for proper accounting
            item['gross'] = -abs(item['gross'])
            item['net_total'] = -abs(item['net_total'])
            item['tax_amount'] = -abs(item['tax_amount'])
            item['grand_total'] = -abs(item['grand_total'])

        # Combine and sort by date
        combined = purchase_data + return_data
        combined.sort(key=lambda x: x['date'])

        return combined

    def _get_report_values(self):
        """Get values to pass to the report template"""
        self.ensure_one()

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
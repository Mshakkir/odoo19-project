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
        """Fetch purchase order data based on filters"""
        self.ensure_one()

        # Search for posted vendor bills (purchase invoices)
        domain = [
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
            ('state', '=', 'posted'),
            ('move_type', '=', 'in_invoice'),
            ('company_id', '=', self.company_id.id)
        ]

        if self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))

        invoices = self.env['account.move'].search(domain, order='invoice_date asc, name asc')

        data = []
        for invoice in invoices:
            # Calculate amounts
            gross_total = sum(line.price_subtotal for line in invoice.invoice_line_ids)
            trade_disc = 0.0  # Calculate discount if your lines have discount field
            for line in invoice.invoice_line_ids:
                if line.discount:
                    discount_amount = (line.price_unit * line.quantity * line.discount) / 100
                    trade_disc += discount_amount

            net_total = gross_total - trade_disc
            tax_amount = invoice.amount_tax
            grand_total = invoice.amount_total

            data.append({
                'date': invoice.invoice_date,
                'vendor': invoice.partner_id.name,
                'invoice_ref': invoice.ref or invoice.name,
                'po_number': ', '.join(invoice.invoice_line_ids.mapped('purchase_line_id.order_id.name')) or '',
                'gross': gross_total,
                'trade_disc': trade_disc,
                'net_total': net_total,
                'add_disc': 0.0,
                'add_cost': 0.0,
                'round_off': invoice.amount_residual_signed if hasattr(invoice, 'amount_residual_signed') else 0.0,
                'adj_amount': 0.0,
                'tax_amount': tax_amount,
                'grand_total': grand_total,
            })

        return data

    def _get_return_data(self):
        """Fetch purchase return (refund) data based on filters"""
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

        refunds = self.env['account.move'].search(domain, order='invoice_date asc, name asc')

        data = []
        for refund in refunds:
            gross_total = sum(line.price_subtotal for line in refund.invoice_line_ids)
            trade_disc = 0.0
            for line in refund.invoice_line_ids:
                if line.discount:
                    discount_amount = (line.price_unit * line.quantity * line.discount) / 100
                    trade_disc += discount_amount

            net_total = gross_total - trade_disc
            tax_amount = refund.amount_tax
            grand_total = refund.amount_total

            data.append({
                'date': refund.invoice_date,
                'vendor': refund.partner_id.name,
                'invoice_ref': refund.ref or refund.name,
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
        """Fetch both purchase and return data"""
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
        }
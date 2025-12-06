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
        data = {
            'report_type': self.report_type,
            'view_type': self.view_type,
            'date_from': self.date_from.strftime('%Y-%m-%d'),
            'date_to': self.date_to.strftime('%Y-%m-%d'),
            'partner_ids': self.partner_ids.ids,
            'include_expense': self.include_expense,
        }

        return self.env.ref('purchase_book.action_report_purchase_book').report_action(self, data=data)

    def _get_purchase_data(self):
        """Fetch purchase order data based on filters"""
        domain = [
            ('date_order', '>=', self.date_from),
            ('date_order', '<=', self.date_to),
            ('state', 'in', ['purchase', 'done'])
        ]

        if self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))

        purchases = self.env['purchase.order'].search(domain, order='date_order asc')

        data = []
        for po in purchases:
            # Get invoice information
            invoices = po.invoice_ids.filtered(lambda inv: inv.state == 'posted' and inv.move_type == 'in_invoice')

            for invoice in invoices:
                gross_total = sum(line.price_subtotal for line in invoice.invoice_line_ids)
                trade_disc = sum(line.discount_amount if hasattr(line, 'discount_amount') else 0
                                 for line in invoice.invoice_line_ids)
                net_total = gross_total - trade_disc
                tax_amount = sum(line.price_total - line.price_subtotal for line in invoice.invoice_line_ids)
                grand_total = invoice.amount_total

                data.append({
                    'date': invoice.invoice_date,
                    'vendor': po.partner_id.name,
                    'invoice_ref': invoice.ref or invoice.name,
                    'po_number': po.name,
                    'gross': gross_total,
                    'trade_disc': trade_disc,
                    'net_total': net_total,
                    'add_disc': 0.0,  # Additional discount if applicable
                    'add_cost': 0.0,  # Additional cost if applicable
                    'round_off': invoice.amount_residual if hasattr(invoice, 'amount_residual') else 0,
                    'adj_amount': 0.0,
                    'tax_amount': tax_amount,
                    'grand_total': grand_total,
                })

        return data

    def _get_return_data(self):
        """Fetch purchase return (refund) data based on filters"""
        domain = [
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
            ('state', '=', 'posted'),
            ('move_type', '=', 'in_refund')
        ]

        if self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))

        refunds = self.env['account.move'].search(domain, order='invoice_date asc')

        data = []
        for refund in refunds:
            gross_total = sum(line.price_subtotal for line in refund.invoice_line_ids)
            trade_disc = 0.0
            net_total = gross_total
            tax_amount = sum(line.price_total - line.price_subtotal for line in refund.invoice_line_ids)
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
        purchase_data = self._get_purchase_data()
        return_data = self._get_return_data()

        # Mark transaction types
        for item in purchase_data:
            item['type'] = 'Purchase'
            item['type_label'] = 'Purchase Invoice'

        for item in return_data:
            item['type'] = 'Return'
            item['type_label'] = 'Purchase Invoice'
            # Make return values negative for proper accounting
            item['gross'] = -item['gross']
            item['net_total'] = -item['net_total']
            item['tax_amount'] = -item['tax_amount']
            item['grand_total'] = -item['grand_total']

        # Combine and sort by date
        combined = purchase_data + return_data
        combined.sort(key=lambda x: x['date'])

        return combined
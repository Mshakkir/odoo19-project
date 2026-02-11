# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class AdvancePaymentReportWizard(models.TransientModel):
    _name = 'advance.payment.report.wizard'
    _description = 'Advance Payment Report Wizard'

    date_from = fields.Date(
        string='Date From',
        required=True,
        default=fields.Date.context_today
    )
    date_to = fields.Date(
        string='Date To',
        required=True,
        default=fields.Date.context_today
    )
    bank_id = fields.Many2one(
        'account.journal',
        string='Bank',
        domain="[('type', '=', 'bank')]"
    )
    vendor_id = fields.Many2one(
        'res.partner',
        string='Vendor',
        domain="[('supplier_rank', '>', 0)]"
    )

    def action_show_report(self):
        """Generate and display the advance payment report"""
        self.ensure_one()

        # Validate date range
        if self.date_from > self.date_to:
            raise UserError('Date From cannot be greater than Date To.')

        # Clear previous report data
        self.env['advance.payment.report'].search([]).unlink()

        # Build domain for searching vendor payments
        domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('payment_type', '=', 'outbound'),  # Vendor payments
            ('partner_type', '=', 'supplier'),
            ('state', '=', 'posted'),  # Only posted payments
        ]

        # Add bank filter if selected
        if self.bank_id:
            domain.append(('journal_id', '=', self.bank_id.id))

        # Add vendor filter if selected
        if self.vendor_id:
            domain.append(('partner_id', '=', self.vendor_id.id))

        # Search for advance payments
        # Looking for payments where the memo/communication contains 'ADVANCE'
        payments = self.env['account.payment'].search(domain)

        # Filter advance payments based on memo
        advance_payments = payments.filtered(
            lambda p: p.ref and 'ADVANCE' in p.ref.upper()
        )

        # Prepare report data
        report_lines = []
        for payment in advance_payments:
            # Get payment method name
            payment_method_name = 'Manual Payment'
            if payment.payment_method_line_id:
                payment_method_name = payment.payment_method_line_id.name

            # Create report line
            report_lines.append({
                'date': payment.date,
                'receipt_number': payment.name or '',
                'payment_method': payment_method_name,
                'vendor_name': payment.partner_id.name or '',
                'amount': payment.amount,
                'currency_id': payment.currency_id.id,
            })

        # Create report records
        if report_lines:
            self.env['advance.payment.report'].create(report_lines)

        # Return action to open list view
        return {
            'name': 'Advance Payment Report',
            'type': 'ir.actions.act_window',
            'res_model': 'advance.payment.report',
            'view_mode': 'list',
            'target': 'current',
        }

    def action_exit(self):
        """Close the wizard"""
        return {'type': 'ir.actions.act_window_close'}# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class AdvancePaymentReportWizard(models.TransientModel):
    _name = 'advance.payment.report.wizard'
    _description = 'Advance Payment Report Wizard'

    date_from = fields.Date(
        string='Date From',
        required=True,
        default=fields.Date.context_today
    )
    date_to = fields.Date(
        string='Date To',
        required=True,
        default=fields.Date.context_today
    )
    bank_id = fields.Many2one(
        'account.journal',
        string='Bank',
        domain="[('type', '=', 'bank')]"
    )
    all_vendors = fields.Boolean(
        string='All Vendors',
        default=True
    )
    vendor_id = fields.Many2one(
        'res.partner',
        string='Vendor',
        domain="[('supplier_rank', '>', 0)]"
    )

    @api.onchange('all_vendors')
    def _onchange_all_vendors(self):
        """Clear vendor selection when All Vendors is checked"""
        if self.all_vendors:
            self.vendor_id = False

    @api.onchange('vendor_id')
    def _onchange_vendor_id(self):
        """Uncheck All Vendors when a specific vendor is selected"""
        if self.vendor_id:
            self.all_vendors = False

    def action_show_report(self):
        """Generate and display the advance payment report"""
        self.ensure_one()

        # Validate date range
        if self.date_from > self.date_to:
            raise UserError('Date From cannot be greater than Date To.')

        # Clear previous report data
        self.env['advance.payment.report'].search([]).unlink()

        # Build domain for searching vendor payments
        domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('payment_type', '=', 'outbound'),  # Vendor payments
            ('partner_type', '=', 'supplier'),
            ('state', '=', 'posted'),  # Only posted payments
        ]

        # Add bank filter if selected
        if self.bank_id:
            domain.append(('journal_id', '=', self.bank_id.id))

        # Add vendor filter if not all vendors
        if not self.all_vendors and self.vendor_id:
            domain.append(('partner_id', '=', self.vendor_id.id))

        # Search for advance payments
        # Looking for payments where the memo/communication contains 'ADVANCE'
        payments = self.env['account.payment'].search(domain)

        # Filter advance payments based on memo
        advance_payments = payments.filtered(
            lambda p: p.ref and 'ADVANCE' in p.ref.upper()
        )

        # Prepare report data
        report_lines = []
        for payment in advance_payments:
            # Get payment method name
            payment_method_name = 'Manual Payment'
            if payment.payment_method_line_id:
                payment_method_name = payment.payment_method_line_id.name

            # Create report line
            report_lines.append({
                'date': payment.date,
                'receipt_number': payment.name or '',
                'payment_method': payment_method_name,
                'vendor_name': payment.partner_id.name or '',
                'amount': payment.amount,
                'currency_id': payment.currency_id.id,
            })

        # Create report records
        if report_lines:
            self.env['advance.payment.report'].create(report_lines)

        # Return action to open list view
        return {
            'name': 'Advance Payment Report',
            'type': 'ir.actions.act_window',
            'res_model': 'advance.payment.report',
            'view_mode': 'list',
            'target': 'current',
        }

    def action_exit(self):
        """Close the wizard"""
        return {'type': 'ir.actions.act_window_close'}
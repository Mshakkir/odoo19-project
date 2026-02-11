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

        # Add logging
        import logging
        _logger = logging.getLogger(__name__)

        _logger.info("=" * 80)
        _logger.info("SEARCH CRITERIA:")
        _logger.info(f"Date From: {self.date_from}")
        _logger.info(f"Date To: {self.date_to}")
        _logger.info(f"Bank: {self.bank_id.name if self.bank_id else 'All Banks'}")
        _logger.info(f"Vendor: {self.vendor_id.name if self.vendor_id else 'All Vendors'}")
        _logger.info("=" * 80)

        # Build domain for searching vendor payments - SIMPLIFIED
        domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ]

        _logger.info(f"Initial domain: {domain}")

        # Add bank filter if selected
        if self.bank_id:
            domain.append(('journal_id', '=', self.bank_id.id))
            _logger.info(f"Added bank filter: journal_id = {self.bank_id.id}")

        # Add vendor filter if not all vendors
        if not self.all_vendors and self.vendor_id:
            domain.append(('partner_id', '=', self.vendor_id.id))
            _logger.info(f"Added vendor filter: partner_id = {self.vendor_id.id}")

        _logger.info(f"Final domain: {domain}")

        # Search for vendor payments using account.payment model
        payments = self.env['account.payment'].search(domain)
        _logger.info(f"Found {len(payments)} total payments with basic domain")

        # Filter to ONLY vendor payments
        # In your system: PAY/ = vendor payments, PREC/ = customer receipts
        vendor_payments = payments.filtered(lambda p: p.name and p.name.startswith('PAY/'))
        _logger.info(f"Filtered to {len(vendor_payments)} vendor payments (PAY/* only)")

        payments = vendor_payments

        # Log payment details
        _logger.info("=" * 80)
        _logger.info("VENDOR PAYMENTS FOUND:")
        for payment in payments:
            _logger.info(f"  {payment.name} - {payment.partner_id.name} - {payment.amount}")
        _logger.info("=" * 80)

        # Search for advance payments
        # Looking for payments where the memo contains 'ADVANCE'
        payments = self.env['account.payment'].search(domain)

        # Filter for advance payments based on memo_new field
        _logger.info("Checking for ADVANCE payments:")
        advance_payments = []
        for payment in payments:
            is_advance = False

            # Check memo_new field for "ADVANCE"
            memo_value = payment.memo_new if hasattr(payment, 'memo_new') else False
            _logger.info(f"  {payment.name}: memo_new = '{memo_value}'")

            if memo_value and 'ADVANCE' in str(memo_value).upper():
                is_advance = True
                _logger.info(f"    ✓ ADVANCE PAYMENT")

            # Add ALL vendor payments to the report (not just advance ones)
            # Users can filter later if needed
            advance_payments.append(payment)

        _logger.info(f"Total payments to show in report: {len(advance_payments)}")
        _logger.info("=" * 80)

        # Convert list back to recordset
        if advance_payments:
            advance_payments = self.env['account.payment'].browse([p.id for p in advance_payments])
        else:
            advance_payments = payments

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
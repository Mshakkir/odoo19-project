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
        # Filter to show only outbound payments (vendor payments, not customer receipts)
        payments = self.env['account.payment'].search(domain)
        _logger.info(f"Found {len(payments)} total payments with basic domain")

        # Filter to ONLY vendor payments (outbound to suppliers)
        # This excludes customer receipts (inbound from customers)
        payments = payments.filtered(lambda p:
                                     p.payment_type == 'outbound' and
                                     p.state == 'posted'
                                     )
        _logger.info(f"Filtered to {len(payments)} outbound posted payments (vendor payments only)")

        # Search for advance payments
        # Looking for payments where the memo contains 'ADVANCE'
        payments = self.env['account.payment'].search(domain)

        # DEBUGGING: Log payment details to help identify the correct field
        _logger.info("=" * 80)
        _logger.info("ADVANCE PAYMENT REPORT DEBUG INFO")
        _logger.info("=" * 80)
        _logger.info(f"Found {len(payments)} total payments in date range")

        # Filter advance payments based on multiple fields
        advance_payments = []
        for payment in payments:
            is_advance = False

            # Log payment details
            _logger.info(f"\n--- Payment: {payment.name} ---")
            _logger.info(f"Date: {payment.date}")
            _logger.info(f"Partner: {payment.partner_id.name}")
            _logger.info(f"Amount: {payment.amount}")

            # Check all possible memo fields
            _logger.info("Checking fields:")

            # Check memo_new field
            if hasattr(payment, 'memo_new'):
                _logger.info(f"  memo_new: '{payment.memo_new}'")
                if payment.memo_new and 'ADVANCE' in str(payment.memo_new).upper():
                    is_advance = True
                    _logger.info("  ✓ MATCHED in memo_new!")

            # Check ref field
            if hasattr(payment, 'ref'):
                _logger.info(f"  ref: '{payment.ref}'")
                if not is_advance and payment.ref and 'ADVANCE' in str(payment.ref).upper():
                    is_advance = True
                    _logger.info("  ✓ MATCHED in ref!")

            # Check narration field
            if hasattr(payment, 'narration'):
                _logger.info(f"  narration: '{payment.narration}'")
                if not is_advance and payment.narration and 'ADVANCE' in str(payment.narration).upper():
                    is_advance = True
                    _logger.info("  ✓ MATCHED in narration!")

            # Check move lines
            if hasattr(payment, 'move_id') and payment.move_id:
                _logger.info(f"  Journal Entry: {payment.move_id.name}")
                for line in payment.move_id.line_ids:
                    _logger.info(f"    Line: {line.name}")
                    if not is_advance and line.name and 'ADVANCE' in str(line.name).upper():
                        is_advance = True
                        _logger.info("    ✓ MATCHED in move line!")
                        break

            # For debugging, show ALL payments
            _logger.info(f"  Final decision: {'ADVANCE PAYMENT' if is_advance else 'REGULAR PAYMENT'}")

            # Add ALL payments for now (debugging mode)
            advance_payments.append(payment)

        _logger.info("=" * 80)
        _logger.info(f"Total advance payments found: {len(advance_payments)}")
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
# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class CustomerAdvanceReceiptWizard(models.TransientModel):
    _name = 'customer.advance.receipt.wizard'
    _description = 'Customer Advance Receipt Report Wizard'

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
    all_journals = fields.Boolean(
        string='All Journals',
        default=False
    )
    journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        domain="[('type', 'in', ['bank', 'cash'])]"
    )
    all_customers = fields.Boolean(
        string='All Customers',
        default=False
    )
    customer_id = fields.Many2one(
        'res.partner',
        string='Customer',
        domain="[('customer_rank', '>', 0)]"
    )

    @api.onchange('all_journals')
    def _onchange_all_journals(self):
        """Clear journal selection when All Journals is checked"""
        if self.all_journals:
            self.journal_id = False

    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        """Uncheck All Journals when a specific journal is selected"""
        if self.journal_id:
            self.all_journals = False

    @api.onchange('all_customers')
    def _onchange_all_customers(self):
        """Clear customer selection when All Customers is checked"""
        if self.all_customers:
            self.customer_id = False

    @api.onchange('customer_id')
    def _onchange_customer_id(self):
        """Uncheck All Customers when a specific customer is selected"""
        if self.customer_id:
            self.all_customers = False

    def action_show_report(self):
        """Generate and display the customer advance receipt report"""
        self.ensure_one()

        # Validate date range
        if self.date_from > self.date_to:
            raise UserError('Date From cannot be greater than Date To.')

        # Clear previous report data
        self.env['customer.advance.receipt.report'].search([]).unlink()

        # Add logging
        import logging
        _logger = logging.getLogger(__name__)

        _logger.info("=" * 80)
        _logger.info("CUSTOMER ADVANCE RECEIPT SEARCH CRITERIA:")
        _logger.info(f"Date From: {self.date_from}")
        _logger.info(f"Date To: {self.date_to}")
        _logger.info(f"Journal: {self.journal_id.name if self.journal_id else 'All Journals'}")
        _logger.info(f"Customer: {self.customer_id.name if self.customer_id else 'All Customers'}")
        _logger.info("=" * 80)

        # Build domain for searching customer receipts
        domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ]

        _logger.info(f"Initial domain: {domain}")

        # Add journal filter if selected
        if not self.all_journals and self.journal_id:
            domain.append(('journal_id', '=', self.journal_id.id))
            _logger.info(f"Added journal filter: journal_id = {self.journal_id.id}")

        # Add customer filter if not all customers
        if not self.all_customers and self.customer_id:
            domain.append(('partner_id', '=', self.customer_id.id))
            _logger.info(f"Added customer filter: partner_id = {self.customer_id.id}")

        _logger.info(f"Final domain: {domain}")

        # Search for customer receipts using account.payment model
        payments = self.env['account.payment'].search(domain)
        _logger.info(f"Found {len(payments)} total payments with basic domain")

        # Filter to ONLY customer receipts
        # In your system: PREC/ = customer receipts, PAY/ = vendor payments
        customer_receipts = payments.filtered(lambda p: p.name and p.name.startswith('PREC/'))
        _logger.info(f"Filtered to {len(customer_receipts)} customer receipts (PREC/* only)")

        # Filter to advance receipts only (using the is_advance_payment checkbox)
        advance_receipts = customer_receipts.filtered(lambda p:
                                                      hasattr(p, 'is_advance_payment') and p.is_advance_payment == True
                                                      )

        _logger.info("=" * 80)
        _logger.info(f"ADVANCE RECEIPTS FOUND: {len(advance_receipts)}")
        for receipt in advance_receipts:
            _logger.info(f"  {receipt.name} - {receipt.partner_id.name} - {receipt.amount}")
        _logger.info("=" * 80)

        # Prepare report data
        report_lines = []
        for receipt in advance_receipts:
            # Get payment method name
            payment_method_name = 'Manual Payment'
            if receipt.payment_method_line_id:
                payment_method_name = receipt.payment_method_line_id.name

            # Create report line
            report_lines.append({
                'date': receipt.date,
                'receipt_number': receipt.name or '',
                'journal_name': receipt.journal_id.name or '',
                'payment_method': payment_method_name,
                'customer_name': receipt.partner_id.name or '',
                'amount': receipt.amount,
                'currency_id': receipt.currency_id.id,
                'payment_id': receipt.id,  # Store payment ID for opening the record
            })

        # Create report records
        if report_lines:
            self.env['customer.advance.receipt.report'].create(report_lines)

        # Return action to open list view
        return {
            'name': 'Customer Advance Receipt Report',
            'type': 'ir.actions.act_window',
            'res_model': 'customer.advance.receipt.report',
            'view_mode': 'list',
            'target': 'current',
        }

    def action_exit(self):
        """Close the wizard"""
        return {'type': 'ir.actions.act_window_close'}










# # -*- coding: utf-8 -*-
#
# from odoo import models, fields, api
# from odoo.exceptions import UserError
#
#
# class CustomerAdvanceReceiptWizard(models.TransientModel):
#     _name = 'customer.advance.receipt.wizard'
#     _description = 'Customer Advance Receipt Report Wizard'
#
#     date_from = fields.Date(
#         string='Date From',
#         required=True,
#         default=fields.Date.context_today
#     )
#     date_to = fields.Date(
#         string='Date To',
#         required=True,
#         default=fields.Date.context_today
#     )
#     all_journals = fields.Boolean(
#         string='All Journals',
#         default=False
#     )
#     journal_id = fields.Many2one(
#         'account.journal',
#         string='Journal',
#         domain="[('type', 'in', ['bank', 'cash'])]"
#     )
#     all_customers = fields.Boolean(
#         string='All Customers',
#         default=False
#     )
#     customer_id = fields.Many2one(
#         'res.partner',
#         string='Customer',
#         domain="[('customer_rank', '>', 0)]"
#     )
#
#     @api.onchange('all_journals')
#     def _onchange_all_journals(self):
#         """Clear journal selection when All Journals is checked"""
#         if self.all_journals:
#             self.journal_id = False
#
#     @api.onchange('journal_id')
#     def _onchange_journal_id(self):
#         """Uncheck All Journals when a specific journal is selected"""
#         if self.journal_id:
#             self.all_journals = False
#
#     @api.onchange('all_customers')
#     def _onchange_all_customers(self):
#         """Clear customer selection when All Customers is checked"""
#         if self.all_customers:
#             self.customer_id = False
#
#     @api.onchange('customer_id')
#     def _onchange_customer_id(self):
#         """Uncheck All Customers when a specific customer is selected"""
#         if self.customer_id:
#             self.all_customers = False
#
#     def action_show_report(self):
#         """Generate and display the customer advance receipt report"""
#         self.ensure_one()
#
#         # Validate date range
#         if self.date_from > self.date_to:
#             raise UserError('Date From cannot be greater than Date To.')
#
#         # Clear previous report data
#         self.env['customer.advance.receipt.report'].search([]).unlink()
#
#         # Add logging
#         import logging
#         _logger = logging.getLogger(__name__)
#
#         _logger.info("=" * 80)
#         _logger.info("CUSTOMER ADVANCE RECEIPT SEARCH CRITERIA:")
#         _logger.info(f"Date From: {self.date_from}")
#         _logger.info(f"Date To: {self.date_to}")
#         _logger.info(f"Journal: {self.journal_id.name if self.journal_id else 'All Journals'}")
#         _logger.info(f"Customer: {self.customer_id.name if self.customer_id else 'All Customers'}")
#         _logger.info("=" * 80)
#
#         # Build domain for searching customer receipts
#         domain = [
#             ('date', '>=', self.date_from),
#             ('date', '<=', self.date_to),
#         ]
#
#         _logger.info(f"Initial domain: {domain}")
#
#         # Add journal filter if selected
#         if not self.all_journals and self.journal_id:
#             domain.append(('journal_id', '=', self.journal_id.id))
#             _logger.info(f"Added journal filter: journal_id = {self.journal_id.id}")
#
#         # Add customer filter if not all customers
#         if not self.all_customers and self.customer_id:
#             domain.append(('partner_id', '=', self.customer_id.id))
#             _logger.info(f"Added customer filter: partner_id = {self.customer_id.id}")
#
#         _logger.info(f"Final domain: {domain}")
#
#         # Search for customer receipts using account.payment model
#         payments = self.env['account.payment'].search(domain)
#         _logger.info(f"Found {len(payments)} total payments with basic domain")
#
#         # Filter to ONLY customer receipts
#         # In your system: PREC/ = customer receipts, PAY/ = vendor payments
#         customer_receipts = payments.filtered(lambda p: p.name and p.name.startswith('PREC/'))
#         _logger.info(f"Filtered to {len(customer_receipts)} customer receipts (PREC/* only)")
#
#         # Filter to advance receipts only (using the is_advance_payment checkbox)
#         advance_receipts = customer_receipts.filtered(lambda p:
#             hasattr(p, 'is_advance_payment') and p.is_advance_payment == True
#         )
#
#         _logger.info("=" * 80)
#         _logger.info(f"ADVANCE RECEIPTS FOUND: {len(advance_receipts)}")
#         for receipt in advance_receipts:
#             _logger.info(f"  {receipt.name} - {receipt.partner_id.name} - {receipt.amount}")
#         _logger.info("=" * 80)
#
#         # Prepare report data
#         report_lines = []
#         for receipt in advance_receipts:
#             # Get payment method name
#             payment_method_name = 'Manual Payment'
#             if receipt.payment_method_line_id:
#                 payment_method_name = receipt.payment_method_line_id.name
#
#             # Create report line
#             report_lines.append({
#                 'date': receipt.date,
#                 'receipt_number': receipt.name or '',
#                 'journal_name': receipt.journal_id.name or '',
#                 'payment_method': payment_method_name,
#                 'customer_name': receipt.partner_id.name or '',
#                 'amount': receipt.amount,
#                 'currency_id': receipt.currency_id.id,
#             })
#
#         # Create report records
#         if report_lines:
#             self.env['customer.advance.receipt.report'].create(report_lines)
#
#         # Return action to open list view
#         return {
#             'name': 'Customer Advance Receipt Report',
#             'type': 'ir.actions.act_window',
#             'res_model': 'customer.advance.receipt.report',
#             'view_mode': 'list',
#             'target': 'current',
#         }
#
#     def action_exit(self):
#         """Close the wizard"""
#         return {'type': 'ir.actions.act_window_close'}

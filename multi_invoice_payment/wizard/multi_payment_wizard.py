#
#
# from odoo import models, fields, api, _
# from odoo.exceptions import UserError, ValidationError
# import logging
#
#
# class MultiPaymentWizard(models.TransientModel):
#     _name = 'multi.payment.wizard'
#     _description = 'Multi Invoice Payment Wizard'
#
#     partner_id = fields.Many2one('res.partner', string='Customer', required=True, domain=[('customer_rank', '>', 0)])
#     payment_date = fields.Date(string='Payment Date', required=True, default=fields.Date.context_today)
#     payment_amount = fields.Monetary(string='Payment Amount', required=True, currency_field='currency_id')
#     journal_id = fields.Many2one('account.journal', string='Payment Journal', required=True,
#                                  domain=[('type', 'in', ['bank', 'cash'])])
#     currency_id = fields.Many2one('res.currency', string='Currency',
#                                   default=lambda self: self.env.company.currency_id)
#     payment_method_line_id = fields.Many2one('account.payment.method.line', string='Payment Method',
#                                              domain="[('journal_id', '=', journal_id)]")
#     memo = fields.Char(string='Memo')
#
#     invoice_line_ids = fields.One2many('multi.payment.invoice.line', 'wizard_id', string='Invoices')
#     total_allocated = fields.Monetary(string='Total Allocated', compute='_compute_total_allocated',
#                                       currency_field='currency_id', store=True)
#     remaining_amount = fields.Monetary(string='Remaining Amount', compute='_compute_remaining_amount',
#                                        currency_field='currency_id', store=True)
#     # auto_allocate = fields.Boolean(string='Auto Allocate', default=False,
#     #                                help='Automatically allocate payment to oldest invoices')
#     auto_allocate = fields.Boolean(string='Display invoices', default=False,
#                                    help='Display invoices')
#
#     # Customer Summary Fields
#     total_invoiced_amount = fields.Monetary(string='Total Invoiced Amount',
#                                             compute='_compute_customer_summary',
#                                             currency_field='currency_id', store=False)
#     total_amount_received = fields.Monetary(string='Total Amount Received',
#                                             compute='_compute_customer_summary',
#                                             currency_field='currency_id', store=False)
#     total_balance_due = fields.Monetary(string='Total Balance Due',
#                                         compute='_compute_customer_summary',
#                                         currency_field='currency_id', store=False)
#
#     @api.depends('partner_id')
#     def _compute_customer_summary(self):
#         """Compute total invoiced amount, amount received and balance due for customer
#         This now properly includes credit entries in the total_amount_received"""
#         for rec in self:
#             if not rec.partner_id:
#                 rec.total_invoiced_amount = 0.0
#                 rec.total_amount_received = 0.0
#                 rec.total_balance_due = 0.0
#                 continue
#
#             # Get all invoices for the customer
#             invoices = self.env['account.move'].search([
#                 ('partner_id', '=', rec.partner_id.id),
#                 ('move_type', '=', 'out_invoice'),
#                 ('state', '=', 'posted'),
#             ])
#
#             total_invoiced = sum(inv.amount_total for inv in invoices)
#             total_residual = sum(inv.amount_residual for inv in invoices)
#
#             # Get receivable account for the customer
#             receivable_accounts = self.env['account.account'].search([
#                 ('account_type', '=', 'asset_receivable'),
#             ])
#
#             # Filter for accounts that belong to current company
#             receivable_account = receivable_accounts.filtered(
#                 lambda acc: rec.env.company in acc.company_ids
#             )
#
#             # Calculate total credits (payments and credit notes) from journal entries
#             # Look for move lines on the receivable account for this partner
#             if receivable_account:
#                 move_lines = self.env['account.move.line'].search([
#                     ('partner_id', '=', rec.partner_id.id),
#                     ('account_id', 'in', receivable_account.ids),
#                     ('move_id.state', '=', 'posted'),
#                 ])
#
#                 # Sum up the credits (negative values) in the receivable account
#                 # Credits represent money received (payments, credit notes, etc.)
#                 total_received = sum(line.credit for line in move_lines)
#             else:
#                 # Fallback: use the previous calculation if no receivable account found
#                 total_received = total_invoiced - total_residual
#
#             rec.total_invoiced_amount = total_invoiced
#             rec.total_amount_received = total_received
#             # Balance Due = Total Invoiced - Total Received (not just invoice residuals)
#             rec.total_balance_due = total_invoiced - total_received
#
#     @api.depends('invoice_line_ids.amount_to_pay', 'invoice_line_ids.selected')
#     def _compute_total_allocated(self):
#         for rec in self:
#             rec.total_allocated = sum(line.amount_to_pay for line in rec.invoice_line_ids if line.selected)
#
#     @api.depends('payment_amount', 'total_allocated')
#     def _compute_remaining_amount(self):
#         for rec in self:
#             rec.remaining_amount = rec.payment_amount - rec.total_allocated
#
#     @api.onchange('partner_id')
#     def _onchange_partner_id(self):
#         """Clear invoice lines when customer changes"""
#         # IMPORTANT: Clear invoice lines when customer changes
#         self.invoice_line_ids = [(5, 0, 0)]  # Delete all records
#         self.auto_allocate = False  # Reset auto allocate
#
#     def action_view_customer_invoices(self):
#         """View all invoices for the selected customer in a popup dialog"""
#         self.ensure_one()
#         if not self.partner_id:
#             raise UserError(_('Please select a customer first.'))
#
#         invoices = self.env['account.move'].search([
#             ('partner_id', '=', self.partner_id.id),
#             ('move_type', '=', 'out_invoice'),
#             ('state', '=', 'posted'),
#         ], order='invoice_date desc')
#
#         if not invoices:
#             return {
#                 'type': 'ir.actions.client',
#                 'tag': 'display_notification',
#                 'params': {
#                     'title': _('No Invoices'),
#                     'message': _('No invoices found for this customer.'),
#                     'type': 'info',
#                 }
#             }
#
#         return {
#             'name': _('Customer Invoices - %s') % self.partner_id.name,
#             'type': 'ir.actions.act_window',
#             'res_model': 'account.move',
#             'view_mode': 'list,form',
#             'domain': [
#                 ('partner_id', '=', self.partner_id.id),
#                 ('move_type', '=', 'out_invoice'),
#                 ('state', '=', 'posted'),
#             ],
#             'context': {'default_partner_id': self.partner_id.id},
#             'target': 'current',
#         }
#
#     def action_view_customer_payments(self):
#         """View all payments received from the selected customer in a list"""
#         self.ensure_one()
#         if not self.partner_id:
#             raise UserError(_('Please select a customer first.'))
#
#         # Search for all payments related to customer
#         payments = self.env['account.payment'].search([
#             ('partner_id', '=', self.partner_id.id),
#         ], order='date desc')
#
#         if not payments:
#             return {
#                 'type': 'ir.actions.client',
#                 'tag': 'display_notification',
#                 'params': {
#                     'title': _('No Payments'),
#                     'message': _('No payments found for this customer.'),
#                     'type': 'info',
#                 }
#             }
#
#         # Create payment list display wizard with payment records
#         wizard = self.env['payment.list.display.wizard'].create({
#             'partner_id': self.partner_id.id,
#             'payment_line_ids': [(0, 0, {
#                 'date': payment.date,
#                 'number': payment.name,
#                 'journal_id': payment.journal_id.id,
#                 'payment_method': payment.payment_method_line_id.name if payment.payment_method_line_id else '',
#                 'amount': payment.amount,
#                 'state': payment.state,
#             }) for payment in payments],
#         })
#
#         return {
#             'name': _('Customer Payments - %s') % self.partner_id.name,
#             'type': 'ir.actions.act_window',
#             'res_model': 'payment.list.display.wizard',
#             'res_id': wizard.id,
#             'view_mode': 'form',
#             'target': 'new',
#         }
#
#     @api.onchange('payment_amount', 'auto_allocate')
#     def _onchange_auto_allocate(self):
#         """Auto allocate payment amount to invoices"""
#         if self.auto_allocate and self.payment_amount > 0:
#             remaining = self.payment_amount
#             for line in self.invoice_line_ids.sorted(key=lambda l: (l.invoice_date, l.invoice_number)):
#                 if remaining <= 0:
#                     break
#                 # Allocate minimum of remaining payment or invoice residual
#                 allocate_amount = min(remaining, line.amount_residual)
#                 line.amount_to_pay = allocate_amount
#                 remaining -= allocate_amount
#
#     def action_load_invoices(self):
#         """Load unpaid invoices for the selected customer"""
#         self.ensure_one()
#
#         if not self.partner_id:
#             raise UserError(_('Please select a customer first.'))
#
#         # Clear existing invoice lines
#         self.invoice_line_ids = [(5, 0, 0)]
#
#         # Get all unpaid invoices for the customer
#         unpaid_invoices = self.env['account.move'].search([
#             ('partner_id', '=', self.partner_id.id),
#             ('move_type', '=', 'out_invoice'),
#             ('state', '=', 'posted'),
#             ('payment_state', 'in', ['not_paid', 'partial']),
#         ], order='invoice_date asc')
#
#         if not unpaid_invoices:
#             return {
#                 'type': 'ir.actions.client',
#                 'tag': 'display_notification',
#                 'params': {
#                     'title': _('No Unpaid Invoices'),
#                     'message': _('All invoices for this customer are paid.'),
#                     'type': 'info',
#                 }
#             }
#
#         # Create invoice lines
#         invoice_lines_data = []
#         for invoice in unpaid_invoices:
#             if invoice.amount_residual > 0:  # Only add invoices with outstanding balance
#                 invoice_lines_data.append((0, 0, {
#                     'invoice_id': invoice.id,
#                     'invoice_date': invoice.invoice_date,
#                     'invoice_number': invoice.name,
#                     'amount_total': invoice.amount_total,
#                     'amount_residual': invoice.amount_residual,
#                     'amount_to_pay': 0.0,
#                     'selected': False,
#                 }))
#
#         if invoice_lines_data:
#             self.invoice_line_ids = invoice_lines_data
#             message = _('Loaded %d unpaid invoices for %s') % (len(invoice_lines_data), self.partner_id.name)
#         else:
#             message = _('No invoices with outstanding balance found.')
#
#         return {
#             'type': 'ir.actions.client',
#             'tag': 'display_notification',
#             'params': {
#                 'title': _('Invoices Loaded'),
#                 'message': message,
#                 'type': 'success',
#             }
#         }
#
#     def action_create_payment(self):
#         """Create payment entry"""
#         self.ensure_one()
#
#         selected_lines = self.invoice_line_ids.filtered(lambda l: l.selected)
#
#         if not selected_lines:
#             raise UserError(_('Please select at least one invoice to pay.'))
#
#         _logger = logging.getLogger(__name__)
#         _logger.info("=== Payment Creation Debug ===")
#         _logger.info(f"Total invoice lines: {len(self.invoice_line_ids)}")
#         for line in self.invoice_line_ids:
#             _logger.info(f"Line ID: {line.id}, Invoice ID: {line.invoice_id.id if line.invoice_id else 'None'}, "
#                          f"Invoice Number: {line.invoice_number}, Selected: {line.selected}, Amount: {line.amount_to_pay}")
#
#         # Collect all invoices to pay with valid amounts
#         invoices_to_pay = []
#         for line in selected_lines:
#             _logger.info(f"Processing selected line: {line.invoice_number}, amount_to_pay: {line.amount_to_pay}")
#             if line.amount_to_pay > 0:
#                 invoices_to_pay.append({
#                     'invoice': line.invoice_id,
#                     'amount': line.amount_to_pay
#                 })
#
#         if not invoices_to_pay:
#             # Provide detailed error message
#             error_details = []
#             for line in selected_lines:
#                 error_details.append(f"{line.invoice_number}: {line.amount_to_pay}")
#
#             raise UserError(_(
#                 'Please enter amounts to pay for selected invoices.\n\n'
#                 'Selected invoices and their amounts:\n%s\n\n'
#                 'Note: Please click on the Amount to Pay cell, enter the amount, '
#                 'then click OUTSIDE the row to save the value before clicking Create Payment.'
#             ) % '\n'.join(error_details))
#
#         total_allocated = sum(item['amount'] for item in invoices_to_pay)
#
#         if total_allocated > self.payment_amount:
#             raise ValidationError(_('Total allocated amount (%.2f) cannot exceed payment amount (%.2f)')
#                                   % (total_allocated, self.payment_amount))
#
#         # Create payments
#         payments = self.env['account.payment']
#         for invoice_data in invoices_to_pay:
#             invoice = invoice_data['invoice']
#             amount = invoice_data['amount']
#
#             # Create payment
#             payment_vals = {
#                 'payment_type': 'inbound',
#                 'partner_type': 'customer',
#                 'partner_id': self.partner_id.id,
#                 'amount': amount,
#                 'currency_id': self.currency_id.id,
#                 'date': self.payment_date,
#                 'journal_id': self.journal_id.id,
#             }
#
#             # Add memo/reference if provided
#             if self.memo:
#                 payment_vals['payment_reference'] = self.memo
#             else:
#                 payment_vals['payment_reference'] = _('Payment for %s', invoice.name)
#
#             if self.payment_method_line_id:
#                 payment_vals['payment_method_line_id'] = self.payment_method_line_id.id
#
#             payment = self.env['account.payment'].create(payment_vals)
#             payment.action_post()
#
#             # Reconcile with invoice
#             # In Odoo 19, payment lines are accessed through move_id
#             if payment.move_id:
#                 payment_lines = payment.move_id.line_ids.filtered(
#                     lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable')
#                                  and not line.reconciled
#                 )
#
#                 # Get invoice move lines
#                 invoice_lines = invoice.line_ids.filtered(
#                     lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable')
#                                  and not line.reconciled
#                 )
#
#                 # Reconcile
#                 if payment_lines and invoice_lines:
#                     (payment_lines + invoice_lines).reconcile()
#
#             payments |= payment
#
#         # Show success message with payment details
#         message = _('Payment(s) created successfully!\n\n')
#         message += _('Total Amount: %.2f %s\n') % (self.payment_amount, self.currency_id.symbol or '')
#         message += _('Allocated: %.2f %s\n') % (self.total_allocated, self.currency_id.symbol or '')
#         message += _('Number of invoices paid: %d') % len(invoices_to_pay)
#
#         return {
#             'type': 'ir.actions.client',
#             'tag': 'display_notification',
#             'params': {
#                 'title': _('Payment Created'),
#                 'message': message,
#                 'type': 'success',
#                 'sticky': False,
#                 'next': {'type': 'ir.actions.act_window_close'},
#             }
#         }
#
#
# class MultiPaymentInvoiceLine(models.TransientModel):
#     _name = 'multi.payment.invoice.line'
#     _description = 'Multi Payment Invoice Line'
#
#     wizard_id = fields.Many2one('multi.payment.wizard', string='Wizard', required=True, ondelete='cascade')
#     invoice_id = fields.Many2one('account.move', string='Invoice', required=True, readonly=True)
#     invoice_date = fields.Date(string='Invoice Date', readonly=True)
#     invoice_number = fields.Char(string='Invoice Number', readonly=True)
#     amount_total = fields.Monetary(string='Total Amount', currency_field='currency_id', readonly=True)
#     amount_residual = fields.Monetary(string='Amount Due', currency_field='currency_id', readonly=True)
#     amount_to_pay = fields.Monetary(string='Amount to Pay', currency_field='currency_id')
#     balance_amount = fields.Monetary(string='Balance Amount', compute='_compute_balance_amount',
#                                      currency_field='currency_id', store=False)
#     selected = fields.Boolean(string='Pay', default=False)
#     currency_id = fields.Many2one('res.currency', related='wizard_id.currency_id', string='Currency', readonly=True)
#
#     @api.depends('amount_residual', 'amount_to_pay')
#     def _compute_balance_amount(self):
#         """Calculate balance amount (amount_residual - amount_to_pay)"""
#         for record in self:
#             record.balance_amount = record.amount_residual - record.amount_to_pay
#
#     @api.onchange('selected')
#     def _onchange_selected(self):
#         """Auto-fill amount when checkbox is selected"""
#         if not self.selected:
#             self.amount_to_pay = 0.0
#             return
#
#         # Only auto-fill if amount is currently 0
#         if self.selected and self.amount_to_pay == 0 and self.amount_residual > 0:
#             self.amount_to_pay = self.amount_residual
#
#     @api.constrains('amount_to_pay', 'amount_residual')
#     def _check_amount_to_pay(self):
#         """Validate amount to pay"""
#         for record in self:
#             if record.amount_to_pay > record.amount_residual:
#                 raise ValidationError(
#                     _('Amount to pay (%.2f) cannot exceed the amount due (%.2f) for invoice %s')
#                     % (record.amount_to_pay, record.amount_residual, record.invoice_number)
#                 )
#
#
# class PaymentListDisplayWizard(models.TransientModel):
#     _name = 'payment.list.display.wizard'
#     _description = 'Payment List Display'
#
#     partner_id = fields.Many2one('res.partner', string='Customer', readonly=True)
#     payment_line_ids = fields.One2many('payment.list.display.line', 'wizard_id', string='Payments')
#
#
# class PaymentListDisplayLine(models.TransientModel):
#     _name = 'payment.list.display.line'
#     _description = 'Payment List Display Line'
#
#     wizard_id = fields.Many2one('payment.list.display.wizard', string='Wizard', ondelete='cascade')
#     date = fields.Date(string='Date')
#     number = fields.Char(string='Number')
#     journal_id = fields.Many2one('account.journal', string='Journal')
#     payment_method = fields.Char(string='Payment Method')
#     amount = fields.Monetary(string='Amount', currency_field='currency_id')
#     state = fields.Char(string='State')
#     currency_id = fields.Many2one('res.currency', related='wizard_id.partner_id.company_id.currency_id',
#                                   string='Currency', readonly=True)


from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class MultiPaymentWizard(models.TransientModel):
    _name = 'multi.payment.wizard'
    _description = 'Multi Invoice Payment Wizard'

    partner_id = fields.Many2one('res.partner', string='Customer', required=True, domain=[('customer_rank', '>', 0)])
    payment_date = fields.Date(string='Payment Date', required=True, default=fields.Date.context_today)
    payment_amount = fields.Monetary(string='Payment Amount', required=True, currency_field='currency_id')
    journal_id = fields.Many2one('account.journal', string='Payment Journal', required=True,
                                 domain=[('type', 'in', ['bank', 'cash'])])
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)
    payment_method_line_id = fields.Many2one('account.payment.method.line', string='Payment Method',
                                             domain="[('journal_id', '=', journal_id)]")
    memo = fields.Char(string='Memo')

    invoice_line_ids = fields.One2many('multi.payment.invoice.line', 'wizard_id', string='Invoices')
    total_allocated = fields.Monetary(string='Total Allocated', compute='_compute_total_allocated',
                                      currency_field='currency_id', store=True)
    remaining_amount = fields.Monetary(string='Remaining Amount', compute='_compute_remaining_amount',
                                       currency_field='currency_id', store=True)
    # auto_allocate = fields.Boolean(string='Auto Allocate', default=False,
    #                                help='Automatically allocate payment to oldest invoices')
    auto_allocate = fields.Boolean(string='Display invoices', default=False,
                                   help='Display invoices')

    # Customer Summary Fields
    total_invoiced_amount = fields.Monetary(string='Total Invoiced Amount',
                                            compute='_compute_customer_summary',
                                            currency_field='currency_id', store=False)
    total_amount_received = fields.Monetary(string='Total Amount Received',
                                            compute='_compute_customer_summary',
                                            currency_field='currency_id', store=False)
    total_balance_due = fields.Monetary(string='Total Balance Due',
                                        compute='_compute_customer_summary',
                                        currency_field='currency_id', store=False)

    @api.depends('partner_id')
    def _compute_customer_summary(self):
        """Compute total invoiced amount, amount received and balance due for customer
        This now properly includes credit entries in the total_amount_received"""
        for rec in self:
            if not rec.partner_id:
                rec.total_invoiced_amount = 0.0
                rec.total_amount_received = 0.0
                rec.total_balance_due = 0.0
                continue

            # Get all invoices for the customer
            invoices = self.env['account.move'].search([
                ('partner_id', '=', rec.partner_id.id),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
            ])

            total_invoiced = sum(inv.amount_total for inv in invoices)
            total_residual = sum(inv.amount_residual for inv in invoices)

            # Get receivable account for the customer
            receivable_accounts = self.env['account.account'].search([
                ('account_type', '=', 'asset_receivable'),
            ])

            # Filter for accounts that belong to current company
            receivable_account = receivable_accounts.filtered(
                lambda acc: rec.env.company in acc.company_ids
            )

            # Calculate total credits (payments and credit notes) from journal entries
            # Look for move lines on the receivable account for this partner
            if receivable_account:
                move_lines = self.env['account.move.line'].search([
                    ('partner_id', '=', rec.partner_id.id),
                    ('account_id', 'in', receivable_account.ids),
                    ('move_id.state', '=', 'posted'),
                ])

                # Sum up the credits (negative values) in the receivable account
                # Credits represent money received (payments, credit notes, etc.)
                total_received = sum(line.credit for line in move_lines)
            else:
                # Fallback: use the previous calculation if no receivable account found
                total_received = total_invoiced - total_residual

            rec.total_invoiced_amount = total_invoiced
            rec.total_amount_received = total_received
            # Balance Due = Total Invoiced - Total Received (not just invoice residuals)
            rec.total_balance_due = total_invoiced - total_received

    @api.depends('invoice_line_ids.amount_to_pay', 'invoice_line_ids.selected')
    def _compute_total_allocated(self):
        for rec in self:
            rec.total_allocated = sum(line.amount_to_pay for line in rec.invoice_line_ids if line.selected)

    @api.depends('payment_amount', 'total_allocated')
    def _compute_remaining_amount(self):
        for rec in self:
            rec.remaining_amount = rec.payment_amount - rec.total_allocated

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """Clear invoice lines when customer changes"""
        # IMPORTANT: Clear invoice lines when customer changes
        self.invoice_line_ids = [(5, 0, 0)]  # Delete all records
        self.auto_allocate = False  # Reset auto allocate

    def action_view_customer_invoices(self):
        """View all invoices for the selected customer in a popup dialog"""
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_('Please select a customer first.'))

        invoices = self.env['account.move'].search([
            ('partner_id', '=', self.partner_id.id),
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
        ], order='invoice_date desc')

        if not invoices:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Invoices'),
                    'message': _('No invoices found for this customer.'),
                    'type': 'info',
                }
            }

        return {
            'name': _('Customer Invoices - %s') % self.partner_id.name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [
                ('partner_id', '=', self.partner_id.id),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
            ],
            'context': {'default_partner_id': self.partner_id.id},
            'target': 'current',
        }

    def action_view_customer_payments(self):
        """View all payments received from the selected customer in a list"""
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_('Please select a customer first.'))

        # Search for all payments related to customer
        payments = self.env['account.payment'].search([
            ('partner_id', '=', self.partner_id.id),
        ], order='date desc')

        if not payments:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Payments'),
                    'message': _('No payments found for this customer.'),
                    'type': 'info',
                }
            }

        return {
            'name': _('Customer Payments - %s') % self.partner_id.name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.partner_id.id)],
            'context': {'default_partner_id': self.partner_id.id},
            'target': 'current',
        }

    def action_load_invoices(self):
        """Load unpaid invoices for selected customer"""
        self.ensure_one()

        if not self.partner_id:
            raise UserError(_('Please select a customer first.'))

        # Clear existing lines
        self.invoice_line_ids = [(5, 0, 0)]

        # Get unpaid invoices
        invoices = self.env['account.move'].search([
            ('partner_id', '=', self.partner_id.id),
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ['not_paid', 'partial']),
        ], order='invoice_date asc')

        if not invoices:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Invoices'),
                    'message': _('No unpaid invoices found for this customer.'),
                    'type': 'warning',
                }
            }

        # Create invoice lines
        invoice_lines = []
        for invoice in invoices:
            if invoice.amount_residual > 0:
                invoice_lines.append((0, 0, {
                    'invoice_id': invoice.id,
                    'invoice_number': invoice.name,
                    'invoice_date': invoice.invoice_date,
                    'amount_total': invoice.amount_total,
                    'amount_residual': invoice.amount_residual,
                    'amount_to_pay': 0.0,
                    'selected': False,
                }))

        if invoice_lines:
            self.invoice_line_ids = invoice_lines

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('%d invoice(s) loaded successfully.') % len(invoice_lines),
                'type': 'success',
            }
        }

    def create_payment(self):
        """Create a single consolidated payment and reconcile with selected invoices"""
        self.ensure_one()

        # Get selected lines
        selected_lines = self.invoice_line_ids.filtered(lambda l: l.selected)

        if not selected_lines:
            raise UserError(_('Please select at least one invoice to pay.'))

        _logger.info(f"Total invoice lines: {len(self.invoice_line_ids)}")
        for line in self.invoice_line_ids:
            _logger.info(f"Line ID: {line.id}, Invoice ID: {line.invoice_id.id if line.invoice_id else 'None'}, "
                         f"Invoice Number: {line.invoice_number}, Selected: {line.selected}, Amount: {line.amount_to_pay}")

        # Collect all invoices to pay with valid amounts
        invoices_to_pay = []
        for line in selected_lines:
            _logger.info(f"Processing selected line: {line.invoice_number}, amount_to_pay: {line.amount_to_pay}")
            if line.amount_to_pay > 0:
                invoices_to_pay.append({
                    'invoice': line.invoice_id,
                    'amount': line.amount_to_pay
                })

        if not invoices_to_pay:
            # Provide detailed error message
            error_details = []
            for line in selected_lines:
                error_details.append(f"{line.invoice_number}: {line.amount_to_pay}")

            raise UserError(_(
                'Please enter amounts to pay for selected invoices.\n\n'
                'Selected invoices and their amounts:\n%s\n\n'
                'Note: Please click on the Amount to Pay cell, enter the amount, '
                'then click OUTSIDE the row to save the value before clicking Create Payment.'
            ) % '\n'.join(error_details))

        total_allocated = sum(item['amount'] for item in invoices_to_pay)

        if total_allocated > self.payment_amount:
            raise ValidationError(_('Total allocated amount (%.2f) cannot exceed payment amount (%.2f)')
                                  % (total_allocated, self.payment_amount))

        # ==============================================
        # CREATE ONE CONSOLIDATED PAYMENT
        # ==============================================

        # Prepare payment reference with invoice numbers
        invoice_numbers = [inv_data['invoice'].name for inv_data in invoices_to_pay]
        if self.memo:
            payment_reference = self.memo
        else:
            if len(invoice_numbers) == 1:
                payment_reference = _('Payment for %s') % invoice_numbers[0]
            else:
                payment_reference = _('Payment for %d invoices: %s') % (len(invoice_numbers),
                                                                        ', '.join(invoice_numbers))

        # Create a single payment for the total allocated amount
        payment_vals = {
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_id.id,
            'amount': total_allocated,  # Total amount being allocated
            'currency_id': self.currency_id.id,
            'date': self.payment_date,
            'journal_id': self.journal_id.id,
            'payment_reference': payment_reference,
        }

        if self.payment_method_line_id:
            payment_vals['payment_method_line_id'] = self.payment_method_line_id.id

        # Create and post the payment
        payment = self.env['account.payment'].create(payment_vals)
        payment.action_post()

        _logger.info(f"Created consolidated payment: {payment.name} for amount: {total_allocated}")

        # ==============================================
        # RECONCILE PAYMENT WITH INVOICES
        # ==============================================

        # Get payment move line (the receivable line from the payment)
        payment_move_line = payment.move_id.line_ids.filtered(
            lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable')
                         and not line.reconciled
        )

        if not payment_move_line:
            raise UserError(_('Could not find payment line for reconciliation.'))

        # Collect all invoice move lines to reconcile
        invoice_move_lines = self.env['account.move.line']
        for invoice_data in invoices_to_pay:
            invoice = invoice_data['invoice']

            # Get invoice receivable lines
            invoice_lines = invoice.line_ids.filtered(
                lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable')
                             and not line.reconciled
            )

            invoice_move_lines |= invoice_lines
            _logger.info(f"Added invoice {invoice.name} lines for reconciliation")

        # Reconcile the payment line with all invoice lines
        if payment_move_line and invoice_move_lines:
            lines_to_reconcile = payment_move_line + invoice_move_lines
            _logger.info(f"Reconciling {len(lines_to_reconcile)} lines")
            lines_to_reconcile.reconcile()
            _logger.info("Reconciliation completed successfully")

        # Show success message with payment details
        message = _('Payment created successfully!\n\n')
        message += _('Payment Number: %s\n') % payment.name
        message += _('Total Amount: %.2f %s\n') % (total_allocated, self.currency_id.symbol or '')
        message += _('Number of invoices paid: %d\n') % len(invoices_to_pay)
        message += _('Invoices: %s') % ', '.join(invoice_numbers)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Payment Created'),
                'message': message,
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }


class MultiPaymentInvoiceLine(models.TransientModel):
    _name = 'multi.payment.invoice.line'
    _description = 'Multi Payment Invoice Line'

    wizard_id = fields.Many2one('multi.payment.wizard', string='Wizard', required=True, ondelete='cascade')
    invoice_id = fields.Many2one('account.move', string='Invoice', required=True, readonly=True)
    invoice_date = fields.Date(string='Invoice Date', readonly=True)
    invoice_number = fields.Char(string='Invoice Number', readonly=True)
    amount_total = fields.Monetary(string='Total Amount', currency_field='currency_id', readonly=True)
    amount_residual = fields.Monetary(string='Amount Due', currency_field='currency_id', readonly=True)
    amount_to_pay = fields.Monetary(string='Amount to Pay', currency_field='currency_id')
    balance_amount = fields.Monetary(string='Balance Amount', compute='_compute_balance_amount',
                                     currency_field='currency_id', store=False)
    selected = fields.Boolean(string='Pay', default=False)
    currency_id = fields.Many2one('res.currency', related='wizard_id.currency_id', string='Currency', readonly=True)

    @api.depends('amount_residual', 'amount_to_pay')
    def _compute_balance_amount(self):
        """Calculate balance amount (amount_residual - amount_to_pay)"""
        for record in self:
            record.balance_amount = record.amount_residual - record.amount_to_pay

    @api.onchange('selected')
    def _onchange_selected(self):
        """Auto-fill amount when checkbox is selected"""
        if not self.selected:
            self.amount_to_pay = 0.0
            return

        # Only auto-fill if amount is currently 0
        if self.selected and self.amount_to_pay == 0 and self.amount_residual > 0:
            self.amount_to_pay = self.amount_residual

    @api.constrains('amount_to_pay', 'amount_residual')
    def _check_amount_to_pay(self):
        """Validate amount to pay"""
        for record in self:
            if record.amount_to_pay > record.amount_residual:
                raise ValidationError(
                    _('Amount to pay (%.2f) cannot exceed the amount due (%.2f) for invoice %s')
                    % (record.amount_to_pay, record.amount_residual, record.invoice_number)
                )


class PaymentListDisplayWizard(models.TransientModel):
    _name = 'payment.list.display.wizard'
    _description = 'Payment List Display'

    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True)
    payment_line_ids = fields.One2many('payment.list.display.line', 'wizard_id', string='Payments')


class PaymentListDisplayLine(models.TransientModel):
    _name = 'payment.list.display.line'
    _description = 'Payment List Display Line'

    wizard_id = fields.Many2one('payment.list.display.wizard', string='Wizard', ondelete='cascade')
    date = fields.Date(string='Date')
    number = fields.Char(string='Number')
    journal_id = fields.Many2one('account.journal', string='Journal')
    payment_method = fields.Char(string='Payment Method')
    amount = fields.Monetary(string='Amount', currency_field='currency_id')
    state = fields.Char(string='State')
    currency_id = fields.Many2one('res.currency', related='wizard_id.partner_id.company_id.currency_id',
                                  string='Currency', readonly=True)
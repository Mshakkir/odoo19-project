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

    def action_view_partner_ledger(self):
        """View the partner ledger for the selected customer"""
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_('Please select a customer first.'))

        return {
            'name': _('Partner Ledger - %s') % self.partner_id.name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'list',
            'domain': [
                ('partner_id', '=', self.partner_id.id),
                ('account_id.account_type', 'in', ['asset_receivable', 'liability_payable']),
                ('move_id.state', '=', 'posted'),
            ],
            'context': {
                'search_default_partner_id': self.partner_id.id,
                'default_partner_id': self.partner_id.id,
            },
            'target': 'current',
        }

    def action_load_invoices(self):
        """Load unpaid invoices for the selected customer"""
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_('Please select a customer first.'))

        # Get all unpaid invoices for the customer
        invoices = self.env['account.move'].search([
            ('partner_id', '=', self.partner_id.id),
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ['not_paid', 'partial']),
        ], order='invoice_date')

        if not invoices:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Unpaid Invoices'),
                    'message': _('No unpaid invoices found for this customer.'),
                    'type': 'warning',
                }
            }

        # Create invoice lines
        invoice_line_vals = []
        for invoice in invoices:
            if invoice.amount_residual > 0:
                invoice_line_vals.append((0, 0, {
                    'invoice_id': invoice.id,
                    'invoice_date': invoice.invoice_date,
                    'invoice_number': invoice.name,
                    'amount_total': invoice.amount_total,
                    'amount_residual': invoice.amount_residual,
                    'amount_to_pay': 0.0,
                    'selected': False,
                }))

        # Update the wizard with invoice lines
        self.invoice_line_ids = [(5, 0, 0)]  # Clear existing lines
        self.invoice_line_ids = invoice_line_vals
        self.auto_allocate = True

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Invoices Loaded'),
                'message': _('%d unpaid invoices loaded successfully.') % len(invoice_line_vals),
                'type': 'success',
            }
        }

    def action_create_payment(self):
        """Create payment and reconcile with selected invoices"""
        self.ensure_one()

        # Validations
        if not self.partner_id:
            raise UserError(_('Please select a customer.'))

        if not self.journal_id:
            raise UserError(_('Please select a payment journal.'))

        if self.payment_amount <= 0:
            raise UserError(_('Payment amount must be greater than zero.'))

        # Get selected invoices with amounts
        selected_lines = self.invoice_line_ids.filtered(lambda l: l.selected and l.amount_to_pay > 0)

        if not selected_lines:
            raise UserError(_('Please select at least one invoice to pay.'))

        # Collect invoices and amounts to pay
        invoices_to_pay = []
        total_allocated = 0.0

        for line in selected_lines:
            if line.amount_to_pay > line.amount_residual:
                raise UserError(
                    _('Amount to pay (%.2f) cannot exceed the amount due (%.2f) for invoice %s')
                    % (line.amount_to_pay, line.amount_residual, line.invoice_number)
                )

            invoices_to_pay.append({
                'invoice': line.invoice_id,
                'amount': line.amount_to_pay,
            })
            total_allocated += line.amount_to_pay

        # Validate total allocated does not exceed payment amount
        if total_allocated > self.payment_amount:
            raise UserError(_('Total allocated amount (%.2f) exceeds the payment amount (%.2f).')
                            % (total_allocated, self.payment_amount))

        # ==============================================
        # CREATE ONE SINGLE COMBINED PAYMENT
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
            'amount': total_allocated,  # Use total allocated, not payment_amount
            'currency_id': self.currency_id.id,
            'date': self.payment_date,
            'journal_id': self.journal_id.id,
            'payment_reference': payment_reference,
        }

        if self.payment_method_line_id:
            payment_vals['payment_method_line_id'] = self.payment_method_line_id.id

        # Create the payment
        payment = self.env['account.payment'].create(payment_vals)

        # Post the payment
        payment.action_post()

        # ==============================================
        # CRITICAL FIX: ENSURE PARTNER IS SET ON MOVE
        # ==============================================
        # Explicitly set partner_id on the journal entry and all its lines
        # This ensures the payment appears in the partner ledger
        if payment.move_id:
            # Set partner on the move itself
            payment.move_id.write({'partner_id': self.partner_id.id})

            # Ensure all move lines have the partner set
            for line in payment.move_id.line_ids:
                if not line.partner_id:
                    line.write({'partner_id': self.partner_id.id})

            _logger.info(f"Set partner {self.partner_id.name} on payment move {payment.move_id.name}")

        _logger.info(f"Created combined payment: {payment.name} for amount: {total_allocated}")

        # ==============================================
        # RECONCILE PAYMENT WITH INVOICES
        # ==============================================

        # Get the credit line from payment (this is the receivable account line with credit > 0)
        payment_line = payment.move_id.line_ids.filtered(
            lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable')
                      and l.credit > 0
        )

        if not payment_line:
            raise UserError(_('Could not find payment receivable line for reconciliation.'))

        _logger.info(
            f"Payment line found - Credit: {payment_line.credit}, Account: {payment_line.account_id.name}, Partner: {payment_line.partner_id.name}")

        # Collect all invoice receivable lines (debit lines)
        invoice_lines_to_reconcile = self.env['account.move.line']

        for invoice_data in invoices_to_pay:
            invoice = invoice_data['invoice']

            # Get the invoice receivable line (debit line)
            invoice_line = invoice.line_ids.filtered(
                lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable')
                          and l.debit > 0
            )

            if invoice_line:
                invoice_lines_to_reconcile |= invoice_line
                _logger.info(f"Added invoice {invoice.name} line - Debit: {invoice_line.debit}")

        # Reconcile all together
        if payment_line and invoice_lines_to_reconcile:
            lines_to_reconcile = payment_line + invoice_lines_to_reconcile
            _logger.info(
                f"Reconciling {len(lines_to_reconcile)} lines (1 payment + {len(invoice_lines_to_reconcile)} invoices)")

            try:
                lines_to_reconcile.reconcile()
                _logger.info("Successfully reconciled payment with all invoices")
            except Exception as e:
                _logger.error(f"Reconciliation error: {str(e)}")
                raise UserError(_('Error during reconciliation: %s') % str(e))

        # Show success message
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
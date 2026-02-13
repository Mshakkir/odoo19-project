from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class MultiReceiptWizard(models.TransientModel):
    _name = 'multi.receipt.wizard'
    _description = 'Multi Bill Receipt Wizard'

    vendor_id = fields.Many2one('res.partner', string='Vendor', required=True, domain=[('supplier_rank', '>', 0)])
    receipt_date = fields.Date(string='Receipt Date', required=True, default=fields.Date.context_today)
    receipt_amount = fields.Monetary(string='Receipt Amount', required=True, currency_field='currency_id')
    journal_id = fields.Many2one('account.journal', string='Receipt Journal', required=True,
                                 domain=[('type', 'in', ['bank', 'cash'])])
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)
    payment_method_line_id = fields.Many2one('account.payment.method.line', string='Payment Method',
                                             domain="[('journal_id', '=', journal_id)]")
    memo = fields.Char(string='Memo')

    invoice_line_ids = fields.One2many('multi.receipt.invoice.line', 'wizard_id', string='Bills')
    total_allocated = fields.Monetary(string='Total Allocated', compute='_compute_total_allocated',
                                      currency_field='currency_id', store=True)
    remaining_amount = fields.Monetary(string='Remaining Amount', compute='_compute_remaining_amount',
                                       currency_field='currency_id', store=True)
    auto_allocate = fields.Boolean(string='Display bills', default=False,
                                   help='Display bills')

    total_invoiced_amount = fields.Monetary(string='Total Invoiced Amount',
                                            compute='_compute_vendor_summary',
                                            currency_field='currency_id', store=False)
    total_amount_paid = fields.Monetary(string='Total Amount Paid',
                                        compute='_compute_vendor_summary',
                                        currency_field='currency_id', store=False)
    total_balance_due = fields.Monetary(string='Total Balance Due',
                                        compute='_compute_vendor_summary',
                                        currency_field='currency_id', store=False)

    @api.depends('vendor_id')
    def _compute_vendor_summary(self):
        for rec in self:
            if not rec.vendor_id:
                rec.total_invoiced_amount = 0.0
                rec.total_amount_paid = 0.0
                rec.total_balance_due = 0.0
                continue

            bills = self.env['account.move'].search([
                ('partner_id', '=', rec.vendor_id.id),
                ('move_type', '=', 'in_invoice'),
                ('state', '=', 'posted'),
            ])

            total_invoiced = sum(inv.amount_total for inv in bills)

            payable_accounts = self.env['account.account'].search([
                ('account_type', '=', 'liability_payable'),
            ])

            payable_account = payable_accounts.filtered(
                lambda acc: rec.env.company in acc.company_ids
            )

            if payable_account:
                move_lines = self.env['account.move.line'].search([
                    ('partner_id', '=', rec.vendor_id.id),
                    ('account_id', 'in', payable_account.ids),
                    ('move_id.state', '=', 'posted'),
                ])

                total_paid = sum(line.debit for line in move_lines)
            else:
                total_invoiced_bills = sum(inv.amount_total for inv in bills)
                total_residual = sum(inv.amount_residual for inv in bills)
                total_paid = total_invoiced_bills - total_residual

            rec.total_invoiced_amount = total_invoiced
            rec.total_amount_paid = total_paid
            rec.total_balance_due = total_invoiced - total_paid

    @api.depends('invoice_line_ids.amount_to_pay', 'invoice_line_ids.selected')
    def _compute_total_allocated(self):
        for rec in self:
            rec.total_allocated = sum(line.amount_to_pay for line in rec.invoice_line_ids if line.selected)

    @api.depends('receipt_amount', 'total_allocated')
    def _compute_remaining_amount(self):
        for rec in self:
            rec.remaining_amount = rec.receipt_amount - rec.total_allocated

    @api.onchange('vendor_id')
    def _onchange_vendor_id(self):
        self.invoice_line_ids = [(5, 0, 0)]
        self.auto_allocate = False

    def action_view_vendor_bills(self):
        self.ensure_one()
        if not self.vendor_id:
            raise UserError(_('Please select a vendor first.'))

        bills = self.env['account.move'].search([
            ('partner_id', '=', self.vendor_id.id),
            ('move_type', '=', 'in_invoice'),
            ('state', '=', 'posted'),
        ], order='invoice_date desc')

        if not bills:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Bills'),
                    'message': _('No bills found for this vendor.'),
                    'type': 'info',
                }
            }

        return {
            'name': _('Vendor Bills - %s') % self.vendor_id.name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [
                ('partner_id', '=', self.vendor_id.id),
                ('move_type', '=', 'in_invoice'),
                ('state', '=', 'posted'),
            ],
            'context': {'default_partner_id': self.vendor_id.id},
            'target': 'current',
        }

    def action_view_vendor_payments(self):
        self.ensure_one()
        if not self.vendor_id:
            raise UserError(_('Please select a vendor first.'))

        payments = self.env['account.payment'].search([
            ('partner_id', '=', self.vendor_id.id),
            ('partner_type', '=', 'supplier'),
        ], order='date desc')

        if not payments:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Payments'),
                    'message': _('No payments found for this vendor.'),
                    'type': 'info',
                }
            }

        return {
            'name': _('Vendor Payments - %s') % self.vendor_id.name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'list,form',
            'domain': [
                ('partner_id', '=', self.vendor_id.id),
                ('partner_type', '=', 'supplier'),
            ],
            'context': {'default_partner_id': self.vendor_id.id},
            'target': 'current',
        }

    def action_view_partner_ledger(self):
        """View the partner ledger for the selected vendor"""
        self.ensure_one()
        if not self.vendor_id:
            raise UserError(_('Please select a vendor first.'))

        return {
            'name': _('Partner Ledger - %s') % self.vendor_id.name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'list',
            'domain': [
                ('partner_id', '=', self.vendor_id.id),
                ('account_id.account_type', 'in', ['asset_receivable', 'liability_payable']),
                ('move_id.state', '=', 'posted'),
            ],
            'context': {
                'search_default_partner_id': self.vendor_id.id,
                'default_partner_id': self.vendor_id.id,
            },
            'target': 'current',
        }

    @api.onchange('receipt_amount', 'auto_allocate')
    def _onchange_auto_allocate(self):
        if self.auto_allocate and self.receipt_amount > 0:
            remaining = self.receipt_amount
            for line in self.invoice_line_ids.sorted(key=lambda l: (l.invoice_date, l.invoice_number)):
                if remaining <= 0:
                    break
                if line.amount_residual > 0:
                    amount_to_allocate = min(remaining, line.amount_residual)
                    line.selected = True
                    line.amount_to_pay = amount_to_allocate
                    remaining -= amount_to_allocate

    def action_load_bills(self):
        self.ensure_one()
        if not self.vendor_id:
            raise UserError(_('Please select a vendor first.'))

        bills = self.env['account.move'].search([
            ('partner_id', '=', self.vendor_id.id),
            ('move_type', '=', 'in_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ['not_paid', 'partial']),
        ], order='invoice_date')

        invoice_lines_data = []
        for bill in bills:
            if bill.amount_residual > 0:
                invoice_lines_data.append((0, 0, {
                    'invoice_id': bill.id,
                    'invoice_date': bill.invoice_date,
                    'invoice_number': bill.name,
                    'amount_total': bill.amount_total,
                    'amount_residual': bill.amount_residual,
                    'amount_to_pay': 0.0,
                    'selected': False,
                }))

        self.invoice_line_ids = [(5, 0, 0)]
        if invoice_lines_data:
            self.invoice_line_ids = invoice_lines_data
            message = _('Loaded %d unpaid bills for %s') % (len(invoice_lines_data), self.vendor_id.name)
        else:
            message = _('No bills with outstanding balance found.')

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Bills Loaded'),
                'message': message,
                'type': 'success',
            }
        }

    def action_create_payment(self):
        """Create ONE COMBINED payment and reconcile with selected bills"""
        self.ensure_one()

        # Validations
        if not self.vendor_id:
            raise UserError(_('Please select a vendor.'))

        if not self.journal_id:
            raise UserError(_('Please select a payment journal.'))

        if self.receipt_amount <= 0:
            raise UserError(_('Payment amount must be greater than zero.'))

        # Get selected bills with amounts
        selected_lines = self.invoice_line_ids.filtered(lambda l: l.selected and l.amount_to_pay > 0)

        if not selected_lines:
            raise UserError(_('Please select at least one bill to pay.'))

        # Collect bills and amounts to pay
        bills_to_pay = []
        total_allocated = 0.0

        for line in selected_lines:
            if line.amount_to_pay > line.amount_residual:
                raise UserError(
                    _('Amount to pay (%.2f) cannot exceed the amount due (%.2f) for bill %s')
                    % (line.amount_to_pay, line.amount_residual, line.invoice_number)
                )

            bills_to_pay.append({
                'bill': line.invoice_id,
                'amount': line.amount_to_pay,
            })
            total_allocated += line.amount_to_pay

        # Validate total allocated does not exceed payment amount
        if total_allocated > self.receipt_amount:
            raise UserError(_('Total allocated amount (%.2f) exceeds the payment amount (%.2f).')
                                  % (total_allocated, self.receipt_amount))

        # ==============================================
        # CREATE ONE SINGLE COMBINED PAYMENT
        # ==============================================

        # Prepare payment reference with bill numbers
        bill_numbers = [bill_data['bill'].name for bill_data in bills_to_pay]
        if self.memo:
            payment_reference = self.memo
        else:
            if len(bill_numbers) == 1:
                payment_reference = _('Payment for %s') % bill_numbers[0]
            else:
                payment_reference = _('Payment for %d bills: %s') % (len(bill_numbers),
                                                                        ', '.join(bill_numbers))

        # Create a single payment for the total allocated amount
        payment_vals = {
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'partner_id': self.vendor_id.id,
            'amount': total_allocated,  # Use total allocated, not receipt_amount
            'currency_id': self.currency_id.id,
            'date': self.receipt_date,
            'journal_id': self.journal_id.id,
            'payment_reference': payment_reference,
        }

        if self.payment_method_line_id:
            payment_vals['payment_method_line_id'] = self.payment_method_line_id.id

        # Create the payment
        payment = self.env['account.payment'].create(payment_vals)

        # Post the payment
        payment.action_post()

        _logger.info(f"Created combined payment: {payment.name} for amount: {total_allocated}")

        def action_create_payment(self):
            # ... validation code ...

            # Create payment
            payment = self.env['account.payment'].create(payment_vals)

            # Post the payment
            payment.action_post()

            _logger.info(f"Created combined payment: {payment.name} for amount: {total_allocated}")

            # ==============================================
            # SAVE ALLOCATION HISTORY (NEW FEATURE)
            # ==============================================
            # ADD THIS CODE HERE - BEFORE RECONCILE
            allocation_history_vals = []
            for line in selected_lines:
                allocation_history_vals.append({
                    'payment_id': payment.id,
                    'invoice_vendor_bill_id': line.invoice_id.id,
                    'bill_number': line.invoice_number,
                    'bill_date': line.invoice_date,
                    'amount_total': line.amount_total,
                    'amount_due': line.amount_residual,
                    'amount_paid': line.amount_to_pay,
                    'balance_after_payment': line.balance_amount,
                    'currency_id': self.currency_id.id,
                })

            # Create all allocation history records at once
            self.env['payment.allocation.history'].create(allocation_history_vals)
            _logger.info(
                f"Saved {len(allocation_history_vals)} bill allocation history records for payment {payment.name}")

            # ==============================================
            # RECONCILE PAYMENT WITH BILLS
            # ==============================================
            # Get the debit line from payment...
            payment_line = payment.move_id.line_ids.filtered(...)

            # ... rest of reconciliation code ...

            # Show success message
            message = _('Payment created successfully!\n\n')
            # ...

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                # ...
            }

        # ==============================================
        # RECONCILE PAYMENT WITH BILLS
        # ==============================================

        # Get the debit line from payment (this is the payable account line with debit > 0)
        payment_line = payment.move_id.line_ids.filtered(
            lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable')
                      and l.debit > 0
        )

        if not payment_line:
            raise UserError(_('Could not find payment payable line for reconciliation.'))

        _logger.info(f"Payment line found - Debit: {payment_line.debit}, Account: {payment_line.account_id.name}")

        # Collect all bill payable lines (credit lines)
        bill_lines_to_reconcile = self.env['account.move.line']

        for bill_data in bills_to_pay:
            bill = bill_data['bill']

            # Get the bill payable line (credit line)
            bill_line = bill.line_ids.filtered(
                lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable')
                          and l.credit > 0
            )

            if bill_line:
                bill_lines_to_reconcile |= bill_line
                _logger.info(f"Added bill {bill.name} line - Credit: {bill_line.credit}")

        # Reconcile all together
        if payment_line and bill_lines_to_reconcile:
            lines_to_reconcile = payment_line + bill_lines_to_reconcile
            _logger.info(
                f"Reconciling {len(lines_to_reconcile)} lines (1 payment + {len(bill_lines_to_reconcile)} bills)")

            try:
                lines_to_reconcile.reconcile()
                _logger.info("Successfully reconciled payment with all bills")
            except Exception as e:
                _logger.error(f"Reconciliation error: {str(e)}")
                raise UserError(_('Error during reconciliation: %s') % str(e))

        # Show success message
        message = _('Payment created successfully!\n\n')
        message += _('Payment Number: %s\n') % payment.name
        message += _('Total Amount: %.2f %s\n') % (total_allocated, self.currency_id.symbol or '')
        message += _('Number of bills paid: %d\n') % len(bills_to_pay)
        message += _('Bills: %s') % ', '.join(bill_numbers)

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


class MultiReceiptInvoiceLine(models.TransientModel):
    _name = 'multi.receipt.invoice.line'
    _description = 'Multi Receipt Invoice Line'

    wizard_id = fields.Many2one('multi.receipt.wizard', string='Wizard', required=True, ondelete='cascade')
    invoice_id = fields.Many2one('account.move', string='Bill', required=True, readonly=True)
    invoice_date = fields.Date(string='Bill Date', readonly=True)
    invoice_number = fields.Char(string='Bill Number', readonly=True)
    amount_total = fields.Monetary(string='Total Amount', currency_field='currency_id', readonly=True)
    amount_residual = fields.Monetary(string='Amount Due', currency_field='currency_id', readonly=True)
    amount_to_pay = fields.Monetary(string='Amount to Pay', currency_field='currency_id')
    balance_amount = fields.Monetary(string='Balance Amount', compute='_compute_balance_amount',
                                     currency_field='currency_id', store=False)
    selected = fields.Boolean(string='Pay', default=False)
    currency_id = fields.Many2one('res.currency', related='wizard_id.currency_id', string='Currency', readonly=True)

    @api.depends('amount_residual', 'amount_to_pay')
    def _compute_balance_amount(self):
        for record in self:
            record.balance_amount = record.amount_residual - record.amount_to_pay

    @api.onchange('selected')
    def _onchange_selected(self):
        if not self.selected:
            self.amount_to_pay = 0.0
            return

        if self.selected and self.amount_to_pay == 0 and self.amount_residual > 0:
            self.amount_to_pay = self.amount_residual

    @api.constrains('amount_to_pay', 'amount_residual')
    def _check_amount_to_pay(self):
        for record in self:
            if record.amount_to_pay > record.amount_residual:
                raise ValidationError(
                    _('Amount to pay (%.2f) cannot exceed the amount due (%.2f) for bill %s')
                    % (record.amount_to_pay, record.amount_residual, record.invoice_number)
                )


class ReceiptListDisplayWizard(models.TransientModel):
    _name = 'receipt.list.display.wizard'
    _description = 'Receipt List Display'

    partner_id = fields.Many2one('res.partner', string='Vendor', readonly=True)
    payment_line_ids = fields.One2many('receipt.list.display.line', 'wizard_id', string='Payments')


class ReceiptListDisplayLine(models.TransientModel):
    _name = 'receipt.list.display.line'
    _description = 'Receipt List Display Line'

    wizard_id = fields.Many2one('receipt.list.display.wizard', string='Wizard', ondelete='cascade')
    date = fields.Date(string='Date')
    number = fields.Char(string='Number')
    journal_id = fields.Many2one('account.journal', string='Journal')
    payment_method = fields.Char(string='Payment Method')
    amount = fields.Monetary(string='Amount', currency_field='currency_id')
    state = fields.Char(string='State')
    currency_id = fields.Many2one('res.currency', related='wizard_id.partner_id.company_id.currency_id',
                                  string='Currency', readonly=True)
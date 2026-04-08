from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class MultiPaymentWizard(models.TransientModel):
    _name = 'multi.payment.wizard'
    _description = 'Multi Invoice Payment Wizard'

    partner_id = fields.Many2one(
        'res.partner', string='Customer', required=True,
        domain=[('customer_rank', '>', 0)])
    payment_date = fields.Date(
        string='Payment Date', required=True, default=fields.Date.context_today)
    payment_amount = fields.Monetary(
        string='Payment Amount', required=True, currency_field='currency_id')
    journal_id = fields.Many2one(
        'account.journal', string='Payment Journal', required=True,
        domain=[('type', 'in', ['bank', 'cash'])])

    # Currency: auto-set from customer's assigned currency, fallback to company
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id)

    # Company currency for view invisible comparison
    company_currency_id = fields.Many2one(
        'res.currency', string='Company Currency',
        compute='_compute_currency_names', store=False)

    # Manual exchange rate: 1 [customer currency] = X [company currency]
    manual_currency_exchange_rate = fields.Float(
        string='Exchange Rate', digits=(12, 6), default=1.0,
        help='Rate: 1 [customer currency] = ? [company currency]')

    # Label helpers for  1 EUR = X SAR  display row
    payment_currency_name = fields.Char(
        compute='_compute_currency_names', string='Customer Currency Name')
    company_currency_name = fields.Char(
        compute='_compute_currency_names', string='Company Currency Name')

    payment_method_line_id = fields.Many2one(
        'account.payment.method.line', string='Payment Method',
        domain="[('journal_id', '=', journal_id)]")
    memo = fields.Char(string='Memo')

    invoice_line_ids = fields.One2many(
        'multi.payment.invoice.line', 'wizard_id', string='Invoices')
    total_allocated = fields.Monetary(
        string='Total Allocated', compute='_compute_total_allocated',
        currency_field='currency_id', store=True)
    remaining_amount = fields.Monetary(
        string='Remaining Amount', compute='_compute_remaining_amount',
        currency_field='currency_id', store=True)
    auto_allocate = fields.Boolean(
        string='Display Invoices', default=False, help='Display invoices')
    auto_distribute = fields.Boolean(
        string='Auto Distribute', default=False,
        help='Automatically distribute payment amount to invoices using FIFO method')

    # Customer Summary Fields
    total_invoiced_amount = fields.Monetary(
        string='Total Invoiced Amount', compute='_compute_customer_summary',
        currency_field='currency_id', store=False)
    total_amount_received = fields.Monetary(
        string='Total Amount Received', compute='_compute_customer_summary',
        currency_field='currency_id', store=False)
    total_balance_due = fields.Monetary(
        string='Total Balance Due', compute='_compute_customer_summary',
        currency_field='currency_id', store=False)

    # -------------------------------------------------------
    # Helpers
    # -------------------------------------------------------
    def _get_customer_currency(self, partner):
        """Return the currency assigned to the customer, fallback to company currency."""
        if not partner:
            return self.env.company.currency_id
        p = partner.commercial_partner_id
        if hasattr(p, 'property_purchase_currency_id') and p.property_purchase_currency_id:
            return p.property_purchase_currency_id
        if p.currency_id:
            return p.currency_id
        return self.env.company.currency_id

    # -------------------------------------------------------
    # Computes
    # -------------------------------------------------------
    @api.depends('currency_id')
    def _compute_currency_names(self):
        company_currency = self.env.company.currency_id
        for rec in self:
            rec.payment_currency_name = rec.currency_id.name or ''
            rec.company_currency_name = company_currency.name or ''
            rec.company_currency_id = company_currency

    @api.depends('partner_id', 'currency_id')
    def _compute_customer_summary(self):
        for rec in self:
            if not rec.partner_id:
                rec.total_invoiced_amount = 0.0
                rec.total_amount_received = 0.0
                rec.total_balance_due = 0.0
                continue

            company_currency = rec.env.company.currency_id
            customer_currency = rec._get_customer_currency(rec.partner_id)
            today = fields.Date.context_today(rec)

            invoices = rec.env['account.move'].search([
                ('partner_id', '=', rec.partner_id.id),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
            ])

            total_invoiced = 0.0
            for inv in invoices:
                amt = inv.amount_total
                if inv.currency_id and inv.currency_id != customer_currency:
                    amt = inv.currency_id._convert(
                        amt, customer_currency, rec.env.company, today)
                total_invoiced += amt

            receivable_accounts = rec.env['account.account'].search([
                ('account_type', '=', 'asset_receivable'),
                ('company_ids', 'in', rec.env.company.id),
            ])

            total_received = 0.0
            if receivable_accounts:
                move_lines = rec.env['account.move.line'].search([
                    ('partner_id', '=', rec.partner_id.id),
                    ('account_id', 'in', receivable_accounts.ids),
                    ('move_id.state', '=', 'posted'),
                ])
                for ml in move_lines:
                    amt = ml.credit
                    ml_currency = ml.currency_id or company_currency
                    if ml_currency != customer_currency:
                        amt = ml_currency._convert(
                            amt, customer_currency, rec.env.company, today)
                    total_received += amt
            else:
                total_residual = sum(
                    inv.currency_id._convert(
                        inv.amount_residual, customer_currency, rec.env.company, today)
                    if inv.currency_id != customer_currency
                    else inv.amount_residual
                    for inv in invoices
                )
                total_received = total_invoiced - total_residual

            rec.total_invoiced_amount = total_invoiced
            rec.total_amount_received = total_received
            rec.total_balance_due = total_invoiced - total_received

    @api.depends('invoice_line_ids.amount_to_pay', 'invoice_line_ids.selected')
    def _compute_total_allocated(self):
        for rec in self:
            rec.total_allocated = sum(
                line.amount_to_pay for line in rec.invoice_line_ids if line.selected)

    @api.depends('payment_amount', 'total_allocated')
    def _compute_remaining_amount(self):
        for rec in self:
            rec.remaining_amount = rec.payment_amount - rec.total_allocated

    # -------------------------------------------------------
    # Onchanges
    # -------------------------------------------------------
    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        self.invoice_line_ids = [(5, 0, 0)]
        self.auto_allocate = False
        self.auto_distribute = False
        # Auto-set currency from customer
        self.currency_id = self._get_customer_currency(self.partner_id)

    @api.onchange('currency_id')
    def _onchange_currency_id_rate(self):
        """Auto-fill manual rate from Odoo live rate when currency changes."""
        company_currency = self.env.company.currency_id
        if self.currency_id and self.currency_id != company_currency:
            rate = self.env['res.currency']._get_conversion_rate(
                self.currency_id,
                company_currency,
                self.env.company,
                self.payment_date or fields.Date.today(),
            )
            self.manual_currency_exchange_rate = rate if rate else 1.0
        else:
            self.manual_currency_exchange_rate = 1.0

    @api.onchange('auto_distribute')
    def _onchange_auto_distribute(self):
        if self.auto_distribute:
            self._apply_auto_distribution()
        else:
            for line in self.invoice_line_ids:
                line.selected = False
                line.amount_to_pay = 0.0

    @api.onchange('payment_amount')
    def _onchange_payment_amount(self):
        if self.auto_distribute:
            self._apply_auto_distribution()

    # -------------------------------------------------------
    # FIFO distribution
    # -------------------------------------------------------
    def _apply_auto_distribution(self):
        if not self.invoice_line_ids:
            return
        if not self.payment_amount or self.payment_amount <= 0:
            return
        sorted_lines = self.invoice_line_ids.sorted(key=lambda l: l.invoice_date)
        remaining_payment = self.payment_amount
        for line in sorted_lines:
            if remaining_payment <= 0:
                line.selected = False
                line.amount_to_pay = 0.0
            elif line.amount_residual <= 0:
                line.selected = False
                line.amount_to_pay = 0.0
            else:
                line.selected = True
                if remaining_payment >= line.amount_residual:
                    line.amount_to_pay = line.amount_residual
                    remaining_payment -= line.amount_residual
                else:
                    line.amount_to_pay = remaining_payment
                    remaining_payment = 0.0
        _logger.info(
            f"Auto-distributed {self.payment_amount} across "
            f"{len(sorted_lines)} invoices using FIFO")

    # -------------------------------------------------------
    # Navigation actions
    # -------------------------------------------------------
    def action_view_customer_invoices(self):
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
                'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': _('No Invoices'),
                           'message': _('No invoices found for this customer.'),
                           'type': 'info'}}
        return {
            'name': _('Customer Invoices - %s') % self.partner_id.name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.partner_id.id),
                       ('move_type', '=', 'out_invoice'), ('state', '=', 'posted')],
            'context': {'default_partner_id': self.partner_id.id},
            'target': 'current',
        }

    def action_view_customer_payments(self):
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_('Please select a customer first.'))
        payments = self.env['account.payment'].search([
            ('partner_id', '=', self.partner_id.id),
        ], order='date desc')
        if not payments:
            return {
                'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': _('No Payments'),
                           'message': _('No payments found for this customer.'),
                           'type': 'info'}}
        wizard = self.env['payment.list.display.wizard'].create({
            'partner_id': self.partner_id.id,
        })
        for payment in payments:
            self.env['payment.list.display.line'].create({
                'wizard_id': wizard.id,
                'date': payment.date,
                'number': payment.name,
                'journal_id': payment.journal_id.id,
                'payment_method': payment.payment_method_line_id.name
                    if payment.payment_method_line_id else '',
                'amount': payment.amount,
                'state': dict(payment._fields['state'].selection).get(payment.state),
            })
        return {
            'name': _('Customer Payments - %s') % self.partner_id.name,
            'type': 'ir.actions.act_window',
            'res_model': 'payment.list.display.wizard',
            'view_mode': 'form',
            'res_id': wizard.id,
            'target': 'new',
        }

    # -------------------------------------------------------
    # Load invoices
    # -------------------------------------------------------
    def action_load_invoices(self):
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_('Please select a customer first.'))
        self.invoice_line_ids = [(5, 0, 0)]
        invoices = self.env['account.move'].search([
            ('partner_id', '=', self.partner_id.id),
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ['not_paid', 'partial']),
        ], order='invoice_date asc')
        if not invoices:
            return {
                'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': _('No Unpaid Invoices'),
                           'message': _('No unpaid invoices found for this customer.'),
                           'type': 'info'}}
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
        self.invoice_line_ids = invoice_line_vals
        if self.auto_distribute:
            self._apply_auto_distribution()
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {
                'title': _('Invoices Loaded'),
                'message': _('%d unpaid invoice(s) loaded successfully.') % len(invoice_line_vals),
                'type': 'success'}}

    def action_apply_distribution(self):
        self.ensure_one()
        if not self.invoice_line_ids:
            raise UserError(_('Please load invoices first.'))
        if not self.payment_amount or self.payment_amount <= 0:
            raise UserError(_('Please enter a valid payment amount.'))
        self._apply_auto_distribution()
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {
                'title': _('Distribution Applied'),
                'message': _('Payment amount has been distributed using FIFO method.'),
                'type': 'success'}}

    # -------------------------------------------------------
    # Register payment + history + reconcile
    # -------------------------------------------------------
    def action_register_payment(self):
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_('Please select a customer.'))
        if not self.payment_date:
            raise UserError(_('Please enter the payment date.'))
        if not self.payment_amount or self.payment_amount <= 0:
            raise UserError(_('Please enter a valid payment amount.'))
        if not self.journal_id:
            raise UserError(_('Please select a payment journal.'))

        selected_lines = self.invoice_line_ids.filtered(
            lambda l: l.selected and l.amount_to_pay > 0)
        if not selected_lines:
            raise UserError(_('Please select at least one invoice and enter the amount to pay.'))

        total_allocated = sum(line.amount_to_pay for line in selected_lines)
        if total_allocated > self.payment_amount:
            raise UserError(
                _('Total allocated amount (%.2f) cannot exceed the payment amount (%.2f).')
                % (total_allocated, self.payment_amount))
        if total_allocated <= 0:
            raise UserError(_('Total allocated amount must be greater than zero.'))

        invoices_to_pay = []
        invoice_numbers = []
        for line in selected_lines:
            invoice = line.invoice_id
            amount_to_pay = line.amount_to_pay
            if amount_to_pay > invoice.amount_residual:
                raise UserError(
                    _('Amount to pay (%.2f) for invoice %s exceeds the amount due (%.2f).')
                    % (amount_to_pay, invoice.name, invoice.amount_residual))
            invoices_to_pay.append({
                'invoice': invoice,
                'invoice_number': invoice.name,
                'invoice_date': invoice.invoice_date,
                'amount_total': invoice.amount_total,
                'amount_due': invoice.amount_residual,
                'amount_to_pay': amount_to_pay,
                'balance_after': invoice.amount_residual - amount_to_pay,
            })
            invoice_numbers.append(invoice.name)

        payment_vals = {
            'partner_id': self.partner_id.id,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'amount': total_allocated,
            'date': self.payment_date,
            'journal_id': self.journal_id.id,
            'currency_id': self.currency_id.id,
            'memo': self.memo or (
                f"Payment for {', '.join(invoice_numbers[:3])}"
                f"{'...' if len(invoice_numbers) > 3 else ''}"),
        }
        if self.payment_method_line_id:
            payment_vals['payment_method_line_id'] = self.payment_method_line_id.id

        payment = self.env['account.payment'].with_context(
            default_partner_id=self.partner_id.id
        ).create(payment_vals)
        payment.action_post()

        if payment.move_id and self.memo:
            try:
                payment.move_id.write({'ref': self.memo})
            except Exception as e:
                _logger.warning(f"Could not set memo on move: {str(e)}")

        allocation_history_vals = []
        for invoice_data in invoices_to_pay:
            allocation_history_vals.append({
                'payment_id': payment.id,
                'invoice_id': invoice_data['invoice'].id,
                'invoice_number': invoice_data['invoice_number'],
                'invoice_date': invoice_data['invoice_date'],
                'amount_total': invoice_data['amount_total'],
                'amount_due': invoice_data['amount_due'],
                'amount_paid': invoice_data['amount_to_pay'],
                'balance_after_payment': invoice_data['balance_after'],
                'currency_id': self.currency_id.id,
                'memo': self.memo or '',
            })
        self.env['payment.allocation.history'].create(allocation_history_vals)

        payment_line = payment.move_id.line_ids.filtered(
            lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable')
                      and l.credit > 0)
        if not payment_line:
            raise UserError(_('Could not find payment receivable line for reconciliation.'))

        invoice_lines_to_reconcile = self.env['account.move.line']
        for invoice_data in invoices_to_pay:
            invoice = invoice_data['invoice']
            invoice_line = invoice.line_ids.filtered(
                lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable')
                          and l.debit > 0)
            if invoice_line:
                invoice_lines_to_reconcile |= invoice_line

        if payment_line and invoice_lines_to_reconcile:
            try:
                (payment_line + invoice_lines_to_reconcile).reconcile()
            except Exception as e:
                raise UserError(_('Error during reconciliation: %s') % str(e))

        message = _('Payment created successfully!\n\n')
        message += _('Payment Number: %s\n') % payment.name
        message += _('Total Amount: %.2f %s\n') % (total_allocated, self.currency_id.symbol or '')
        message += _('Number of invoices paid: %d\n') % len(invoices_to_pay)
        message += _('Invoices: %s') % ', '.join(invoice_numbers)

        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {
                'title': _('Payment Created'), 'message': message,
                'type': 'success', 'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }}


class MultiPaymentInvoiceLine(models.TransientModel):
    _name = 'multi.payment.invoice.line'
    _description = 'Multi Payment Invoice Line'

    wizard_id = fields.Many2one(
        'multi.payment.wizard', string='Wizard', required=True, ondelete='cascade')
    invoice_id = fields.Many2one(
        'account.move', string='Invoice', required=True, readonly=True)
    invoice_date = fields.Date(string='Invoice Date', readonly=True)
    invoice_number = fields.Char(string='Invoice Number', readonly=True)
    amount_total = fields.Monetary(
        string='Total Amount', currency_field='currency_id', readonly=True)
    amount_residual = fields.Monetary(
        string='Amount Due', currency_field='currency_id', readonly=True)
    amount_to_pay = fields.Monetary(
        string='Amount to Pay', currency_field='currency_id')
    balance_amount = fields.Monetary(
        string='Balance Amount', compute='_compute_balance_amount',
        currency_field='currency_id', store=False)
    selected = fields.Boolean(string='Pay', default=False)
    currency_id = fields.Many2one(
        'res.currency', related='wizard_id.currency_id', string='Currency', readonly=True)

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
                    _('Amount to pay (%.2f) cannot exceed the amount due (%.2f) for invoice %s')
                    % (record.amount_to_pay, record.amount_residual, record.invoice_number))


class PaymentListDisplayWizard(models.TransientModel):
    _name = 'payment.list.display.wizard'
    _description = 'Payment List Display'

    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True)
    payment_line_ids = fields.One2many(
        'payment.list.display.line', 'wizard_id', string='Payments')


class PaymentListDisplayLine(models.TransientModel):
    _name = 'payment.list.display.line'
    _description = 'Payment List Display Line'

    wizard_id = fields.Many2one(
        'payment.list.display.wizard', string='Wizard', ondelete='cascade')
    date = fields.Date(string='Date')
    number = fields.Char(string='Number')
    journal_id = fields.Many2one('account.journal', string='Journal')
    payment_method = fields.Char(string='Payment Method')
    amount = fields.Monetary(string='Amount', currency_field='currency_id')
    state = fields.Char(string='State')
    currency_id = fields.Many2one(
        'res.currency',
        related='wizard_id.partner_id.company_id.currency_id',
        string='Currency', readonly=True)










# from odoo import models, fields, api, _
# from odoo.exceptions import UserError, ValidationError
# import logging
#
# _logger = logging.getLogger(__name__)
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
#     auto_allocate = fields.Boolean(string='Display invoices', default=False,
#                                    help='Display invoices')
#     auto_distribute = fields.Boolean(string='Auto Distribute', default=False,
#                                      help='Automatically distribute payment amount to invoices using FIFO method')
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
#         self.auto_distribute = False  # Reset auto distribute
#
#     @api.onchange('auto_distribute')
#     def _onchange_auto_distribute(self):
#         """Automatically distribute payment amount to invoices using FIFO when auto_distribute is enabled"""
#         if self.auto_distribute:
#             self._apply_auto_distribution()
#         else:
#             # When disabled, clear all allocations
#             for line in self.invoice_line_ids:
#                 line.selected = False
#                 line.amount_to_pay = 0.0
#
#     @api.onchange('payment_amount')
#     def _onchange_payment_amount(self):
#         """Reapply distribution when payment amount changes and auto_distribute is enabled"""
#         if self.auto_distribute:
#             self._apply_auto_distribution()
#
#     def _apply_auto_distribution(self):
#         """Apply FIFO distribution logic"""
#         if not self.invoice_line_ids:
#             return
#
#         if not self.payment_amount or self.payment_amount <= 0:
#             return
#
#         # Sort invoice lines by date (FIFO - First In First Out)
#         sorted_lines = self.invoice_line_ids.sorted(key=lambda l: l.invoice_date)
#
#         remaining_payment = self.payment_amount
#
#         # Create list to store updates
#         updates = []
#
#         for line in sorted_lines:
#             if remaining_payment <= 0:
#                 # No more payment to distribute
#                 line.selected = False
#                 line.amount_to_pay = 0.0
#             elif line.amount_residual <= 0:
#                 # Invoice already fully paid
#                 line.selected = False
#                 line.amount_to_pay = 0.0
#             else:
#                 # Allocate payment to this invoice
#                 line.selected = True
#
#                 if remaining_payment >= line.amount_residual:
#                     # Full payment for this invoice
#                     line.amount_to_pay = line.amount_residual
#                     remaining_payment -= line.amount_residual
#                 else:
#                     # Partial payment for this invoice
#                     line.amount_to_pay = remaining_payment
#                     remaining_payment = 0.0
#
#         _logger.info(f"Auto-distributed {self.payment_amount} across {len(sorted_lines)} invoices using FIFO")
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
#         # Create wizard to display payment lines
#         wizard = self.env['payment.list.display.wizard'].create({
#             'partner_id': self.partner_id.id,
#         })
#
#         # Create payment lines
#         for payment in payments:
#             self.env['payment.list.display.line'].create({
#                 'wizard_id': wizard.id,
#                 'date': payment.date,
#                 'number': payment.name,
#                 'journal_id': payment.journal_id.id,
#                 'payment_method': payment.payment_method_line_id.name if payment.payment_method_line_id else '',
#                 'amount': payment.amount,
#                 'state': dict(payment._fields['state'].selection).get(payment.state),
#             })
#
#         return {
#             'name': _('Customer Payments - %s') % self.partner_id.name,
#             'type': 'ir.actions.act_window',
#             'res_model': 'payment.list.display.wizard',
#             'view_mode': 'form',
#             'res_id': wizard.id,
#             'target': 'new',
#         }
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
#         # Search for unpaid posted invoices
#         invoices = self.env['account.move'].search([
#             ('partner_id', '=', self.partner_id.id),
#             ('move_type', '=', 'out_invoice'),
#             ('state', '=', 'posted'),
#             ('payment_state', 'in', ['not_paid', 'partial']),
#         ], order='invoice_date asc')  # Order by date for proper FIFO
#
#         if not invoices:
#             return {
#                 'type': 'ir.actions.client',
#                 'tag': 'display_notification',
#                 'params': {
#                     'title': _('No Unpaid Invoices'),
#                     'message': _('No unpaid invoices found for this customer.'),
#                     'type': 'info',
#                 }
#             }
#
#         # Create invoice lines
#         invoice_line_vals = []
#         for invoice in invoices:
#             if invoice.amount_residual > 0:  # Only include invoices with outstanding balance
#                 invoice_line_vals.append((0, 0, {
#                     'invoice_id': invoice.id,
#                     'invoice_date': invoice.invoice_date,
#                     'invoice_number': invoice.name,
#                     'amount_total': invoice.amount_total,
#                     'amount_residual': invoice.amount_residual,
#                     'amount_to_pay': 0.0,
#                     'selected': False,
#                 }))
#
#         self.invoice_line_ids = invoice_line_vals
#
#         _logger.info(f"Loaded {len(invoice_line_vals)} unpaid invoices for customer {self.partner_id.name}")
#
#         # If auto_distribute is enabled, apply distribution after loading
#         if self.auto_distribute:
#             self._apply_auto_distribution()
#
#         return {
#             'type': 'ir.actions.client',
#             'tag': 'display_notification',
#             'params': {
#                 'title': _('Invoices Loaded'),
#                 'message': _('%d unpaid invoice(s) loaded successfully.') % len(invoice_line_vals),
#                 'type': 'success',
#             }
#         }
#
#     def action_apply_distribution(self):
#         """Manually apply FIFO distribution - Button action"""
#         self.ensure_one()
#
#         if not self.invoice_line_ids:
#             raise UserError(_('Please load invoices first.'))
#
#         if not self.payment_amount or self.payment_amount <= 0:
#             raise UserError(_('Please enter a valid payment amount.'))
#
#         self._apply_auto_distribution()
#
#         return {
#             'type': 'ir.actions.client',
#             'tag': 'display_notification',
#             'params': {
#                 'title': _('Distribution Applied'),
#                 'message': _('Payment amount has been distributed using FIFO method.'),
#                 'type': 'success',
#             }
#         }
#
#     def action_register_payment(self):
#         """Register payment against multiple invoices"""
#         self.ensure_one()
#
#         # Validation checks
#         if not self.partner_id:
#             raise UserError(_('Please select a customer.'))
#
#         if not self.payment_date:
#             raise UserError(_('Please enter the payment date.'))
#
#         if not self.payment_amount or self.payment_amount <= 0:
#             raise UserError(_('Please enter a valid payment amount.'))
#
#         if not self.journal_id:
#             raise UserError(_('Please select a payment journal.'))
#
#         # Get selected invoices with amounts
#         selected_lines = self.invoice_line_ids.filtered(lambda l: l.selected and l.amount_to_pay > 0)
#
#         if not selected_lines:
#             raise UserError(_('Please select at least one invoice and enter the amount to pay.'))
#
#         # Calculate total allocated
#         total_allocated = sum(line.amount_to_pay for line in selected_lines)
#
#         if total_allocated > self.payment_amount:
#             raise UserError(
#                 _('Total allocated amount (%.2f) cannot exceed the payment amount (%.2f).')
#                 % (total_allocated, self.payment_amount)
#             )
#
#         if total_allocated <= 0:
#             raise UserError(_('Total allocated amount must be greater than zero.'))
#
#         _logger.info(f"Creating payment for customer {self.partner_id.name}, amount: {total_allocated}")
#
#         # Prepare invoice data for allocation history
#         invoices_to_pay = []
#         invoice_numbers = []
#
#         for line in selected_lines:
#             invoice = line.invoice_id
#             amount_to_pay = line.amount_to_pay
#
#             # Validate amount
#             if amount_to_pay > invoice.amount_residual:
#                 raise UserError(
#                     _('Amount to pay (%.2f) for invoice %s exceeds the amount due (%.2f).')
#                     % (amount_to_pay, invoice.name, invoice.amount_residual)
#                 )
#
#             invoices_to_pay.append({
#                 'invoice': invoice,
#                 'invoice_number': invoice.name,
#                 'invoice_date': invoice.invoice_date,
#                 'amount_total': invoice.amount_total,
#                 'amount_due': invoice.amount_residual,
#                 'amount_to_pay': amount_to_pay,
#                 'balance_after': invoice.amount_residual - amount_to_pay,
#             })
#             invoice_numbers.append(invoice.name)
#
#         # ==============================================
#         # CREATE PAYMENT RECORD
#         # ==============================================
#
#         # Prepare payment values
#         payment_vals = {
#             'partner_id': self.partner_id.id,
#             'payment_type': 'inbound',
#             'partner_type': 'customer',
#             'amount': total_allocated,
#             'date': self.payment_date,
#             'journal_id': self.journal_id.id,
#             'currency_id': self.currency_id.id,
#             'memo': self.memo or f"Payment for {', '.join(invoice_numbers[:3])}{'...' if len(invoice_numbers) > 3 else ''}",
#         }
#
#         # Add payment method if selected
#         if self.payment_method_line_id:
#             payment_vals['payment_method_line_id'] = self.payment_method_line_id.id
#
#         # Create payment with partner context
#         payment = self.env['account.payment'].with_context(
#             default_partner_id=self.partner_id.id
#         ).create(payment_vals)
#
#         _logger.info(f"Created payment record: {payment.name}")
#
#         # Post the payment
#         payment.action_post()
#         _logger.info(f"Posted payment: {payment.name}")
#
#         # Verify partner is set on move and lines
#         if payment.move_id:
#             _logger.info(
#                 f"Payment move: {payment.move_id.name}, Partner: {payment.move_id.partner_id.name if payment.move_id.partner_id else 'NOT SET'}")
#             for line in payment.move_id.line_ids:
#                 _logger.info(
#                     f"Move line - Account: {line.account_id.code}, Partner: {line.partner_id.name if line.partner_id else 'NOT SET'}, Debit: {line.debit}, Credit: {line.credit}")
#
#         # Set memo on the journal entry after posting
#         if payment.move_id and self.memo:
#             try:
#                 payment.move_id.write({'ref': self.memo})
#                 _logger.info(f"Set memo '{self.memo}' on move {payment.move_id.name}")
#             except Exception as e:
#                 _logger.warning(f"Could not set memo on move: {str(e)}")
#
#         # ==============================================
#         # SAVE ALLOCATION HISTORY (UPDATED WITH MEMO)
#         # ==============================================
#         allocation_history_vals = []
#         for invoice_data in invoices_to_pay:
#             allocation_history_vals.append({
#                 'payment_id': payment.id,
#                 'invoice_id': invoice_data['invoice'].id,
#                 'invoice_number': invoice_data['invoice_number'],
#                 'invoice_date': invoice_data['invoice_date'],
#                 'amount_total': invoice_data['amount_total'],
#                 'amount_due': invoice_data['amount_due'],
#                 'amount_paid': invoice_data['amount_to_pay'],
#                 'balance_after_payment': invoice_data['balance_after'],
#                 'currency_id': self.currency_id.id,
#                 'memo': self.memo or '',  # Save memo field
#             })
#
#         # Create all allocation history records at once
#         self.env['payment.allocation.history'].create(allocation_history_vals)
#         _logger.info(f"Saved {len(allocation_history_vals)} allocation history records for payment {payment.name}")
#
#         # ==============================================
#         # RECONCILE PAYMENT WITH INVOICES
#         # ==============================================
#
#         # Get the credit line from payment
#         payment_line = payment.move_id.line_ids.filtered(
#             lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable')
#                       and l.credit > 0
#         )
#
#         if not payment_line:
#             raise UserError(_('Could not find payment receivable line for reconciliation.'))
#
#         _logger.info(
#             f"Payment line - Credit: {payment_line.credit}, Account: {payment_line.account_id.name}, Partner: {payment_line.partner_id.name if payment_line.partner_id else 'NOT SET'}")
#
#         # Collect all invoice receivable lines
#         invoice_lines_to_reconcile = self.env['account.move.line']
#
#         for invoice_data in invoices_to_pay:
#             invoice = invoice_data['invoice']
#             invoice_line = invoice.line_ids.filtered(
#                 lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable')
#                           and l.debit > 0
#             )
#
#             if invoice_line:
#                 invoice_lines_to_reconcile |= invoice_line
#                 _logger.info(
#                     f"Added invoice {invoice.name} line - Debit: {invoice_line.debit}, Partner: {invoice_line.partner_id.name if invoice_line.partner_id else 'NOT SET'}")
#
#         # Reconcile all together
#         if payment_line and invoice_lines_to_reconcile:
#             lines_to_reconcile = payment_line + invoice_lines_to_reconcile
#             _logger.info(
#                 f"Reconciling {len(lines_to_reconcile)} lines (1 payment + {len(invoice_lines_to_reconcile)} invoices)")
#
#             try:
#                 lines_to_reconcile.reconcile()
#                 _logger.info("Successfully reconciled payment with all invoices")
#             except Exception as e:
#                 _logger.error(f"Reconciliation error: {str(e)}")
#                 raise UserError(_('Error during reconciliation: %s') % str(e))
#
#         # Show success message
#         message = _('Payment created successfully!\n\n')
#         message += _('Payment Number: %s\n') % payment.name
#         message += _('Total Amount: %.2f %s\n') % (total_allocated, self.currency_id.symbol or '')
#         message += _('Number of invoices paid: %d\n') % len(invoices_to_pay)
#         message += _('Invoices: %s') % ', '.join(invoice_numbers)
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
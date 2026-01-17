from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


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
    auto_allocate = fields.Boolean(string='Auto Allocate', default=False,
                                   help='Automatically allocate payment to oldest invoices')

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
        """Load unpaid invoices when customer is selected"""
        self.invoice_line_ids = [(5, 0, 0)]  # Clear existing lines
        if self.partner_id:
            invoices = self.env['account.move'].search([
                ('partner_id', '=', self.partner_id.id),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('payment_state', 'in', ['not_paid', 'partial'])
            ], order='invoice_date asc, name asc')

            lines = []
            for invoice in invoices:
                lines.append((0, 0, {
                    'invoice_id': invoice.id,
                    'invoice_date': invoice.invoice_date,
                    'invoice_number': invoice.name,
                    'amount_total': invoice.amount_total,
                    'amount_residual': invoice.amount_residual,
                    'amount_to_pay': 0.0,
                    'selected': False,
                }))
            self.invoice_line_ids = lines

    @api.onchange('payment_amount', 'auto_allocate')
    def _onchange_auto_allocate(self):
        """Auto allocate payment amount to invoices"""
        if self.auto_allocate and self.payment_amount > 0:
            remaining = self.payment_amount
            for line in self.invoice_line_ids.sorted(key=lambda l: (l.invoice_date, l.invoice_number)):
                if remaining <= 0:
                    line.selected = False
                    line.amount_to_pay = 0.0
                else:
                    line.selected = True
                    if remaining >= line.amount_residual:
                        line.amount_to_pay = line.amount_residual
                        remaining -= line.amount_residual
                    else:
                        line.amount_to_pay = remaining
                        remaining = 0.0

    def action_load_invoices(self):
        """Reload invoices - refresh button"""
        self._onchange_partner_id()
        return {'type': 'ir.actions.do_nothing'}

    def action_create_payment(self):
        """Create payment and allocate to selected invoices"""
        self.ensure_one()

        if not self.invoice_line_ids.filtered('selected'):
            raise UserError(_('Please select at least one invoice to pay.'))

        if self.total_allocated > self.payment_amount:
            raise ValidationError(_('Total allocated amount (%.2f) cannot exceed payment amount (%.2f)')
                                  % (self.total_allocated, self.payment_amount))

        selected_lines = self.invoice_line_ids.filtered('selected')

        # Create payment for each selected invoice
        payments = self.env['account.payment']
        for line in selected_lines:
            if line.amount_to_pay <= 0:
                continue

            payment_vals = {
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'partner_id': self.partner_id.id,
                'amount': line.amount_to_pay,
                'currency_id': self.currency_id.id,
                'date': self.payment_date,
                'journal_id': self.journal_id.id,
                'payment_method_line_id': self.payment_method_line_id.id,
                'ref': self.memo or f'Payment for {line.invoice_number}',
            }

            payment = self.env['account.payment'].create(payment_vals)
            payment.action_post()

            # Reconcile payment with invoice
            line.invoice_id.js_assign_outstanding_line(payment.line_ids.filtered(
                lambda l: l.account_id == payment.destination_account_id
            ).id)

            payments |= payment

        # Show success message with payment details
        message = _('Payment(s) created successfully!\n\n')
        message += _('Total Amount: %.2f %s\n') % (self.payment_amount, self.currency_id.symbol)
        message += _('Allocated: %.2f %s\n') % (self.total_allocated, self.currency_id.symbol)
        message += _('Number of invoices paid: %d') % len(selected_lines)

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
    invoice_id = fields.Many2one('account.move', string='Invoice', required=True)
    invoice_date = fields.Date(string='Invoice Date')
    invoice_number = fields.Char(string='Invoice Number')
    amount_total = fields.Monetary(string='Total Amount', currency_field='currency_id')
    amount_residual = fields.Monetary(string='Amount Due', currency_field='currency_id')
    amount_to_pay = fields.Monetary(string='Amount to Pay', currency_field='currency_id')
    selected = fields.Boolean(string='Pay', default=False)
    currency_id = fields.Many2one('res.currency', related='wizard_id.currency_id', string='Currency')

    @api.onchange('selected')
    def _onchange_selected(self):
        """Auto-fill amount when checkbox is selected"""
        if self.selected and self.amount_to_pay == 0:
            remaining = self.wizard_id.payment_amount - self.wizard_id.total_allocated
            if remaining >= self.amount_residual:
                self.amount_to_pay = self.amount_residual
            else:
                self.amount_to_pay = remaining
        elif not self.selected:
            self.amount_to_pay = 0.0

    @api.onchange('amount_to_pay')
    def _onchange_amount_to_pay(self):
        """Validate amount to pay"""
        if self.amount_to_pay > self.amount_residual:
            raise ValidationError(_('Amount to pay cannot exceed the amount due (%.2f)') % self.amount_residual)

        if self.amount_to_pay > 0:
            self.selected = True
        else:
            self.selected = False
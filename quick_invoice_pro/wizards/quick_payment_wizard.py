# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class QuickPaymentWizard(models.TransientModel):
    _name = 'quick.payment.wizard'
    _description = 'Quick Payment Wizard'

    invoice_id = fields.Many2one(
        'account.move',
        string='Invoice',
        required=True,
        readonly=True,
    )

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sale Order',
        readonly=True,
    )

    amount = fields.Monetary(
        string='Payment Amount',
        required=True,
        currency_field='currency_id',
    )

    currency_id = fields.Many2one(
        related='invoice_id.currency_id',
        readonly=True,
    )

    payment_date = fields.Date(
        string='Payment Date',
        required=True,
        default=fields.Date.context_today,
    )

    journal_id = fields.Many2one(
        'account.journal',
        string='Payment Method',
        required=True,
        domain=[('type', 'in', ['cash', 'bank'])],
    )

    memo = fields.Char(
        string='Memo',
    )

    @api.model
    def default_get(self, fields_list):
        """Set default values"""
        res = super().default_get(fields_list)

        # Get default cash journal
        cash_journal = self.env['account.journal'].search([
            ('type', '=', 'cash'),
            ('company_id', '=', self.env.company.id),
        ], limit=1)

        if cash_journal:
            res['journal_id'] = cash_journal.id

        return res

    def action_register_payment(self):
        """Register payment and close invoice"""
        self.ensure_one()

        if self.amount <= 0:
            raise UserError(_('Payment amount must be greater than zero.'))

        # Create payment
        payment_vals = {
            'payment_type': 'inbound',
            'partner_id': self.invoice_id.partner_id.id,
            'amount': self.amount,
            'currency_id': self.currency_id.id,
            'date': self.payment_date,
            'journal_id': self.journal_id.id,
            'ref': self.memo or self.invoice_id.name,
            'payment_method_line_id': self.journal_id.inbound_payment_method_line_ids[0].id,
        }

        payment = self.env['account.payment'].create(payment_vals)
        payment.action_post()

        # Reconcile payment with invoice
        lines_to_reconcile = payment.line_ids | self.invoice_id.line_ids
        lines_to_reconcile = lines_to_reconcile.filtered(
            lambda l: l.account_id == self.invoice_id.line_ids[0].account_id
                      and not l.reconciled
        )

        if lines_to_reconcile:
            lines_to_reconcile.reconcile()

        # Show success message and return to invoice
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Payment registered successfully!'),
                'type': 'success',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.act_window',
                    'res_model': 'account.move',
                    'res_id': self.invoice_id.id,
                    'view_mode': 'form',
                },
            }
        }

    def action_skip_payment(self):
        """Skip payment and return to invoice"""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
        }
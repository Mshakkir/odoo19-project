# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    # Add new memo field
    memo_new = fields.Text(
        string='Memo',
        help='Additional memo or notes for this payment'
    )

    def _create_payment_vals_from_wizard(self, batch_result):
        """Override to include memo_new field when creating payment"""
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)

        # Add the new memo field to payment values
        if self.memo_new:
            payment_vals['memo_new'] = self.memo_new

        return payment_vals

    def _create_payment_vals_from_batch(self, batch_result):
        """Override to include memo_new field when creating payment from batch"""
        payment_vals = super()._create_payment_vals_from_batch(batch_result)

        # Add the new memo field to payment values
        if self.memo_new:
            payment_vals['memo_new'] = self.memo_new

        return payment_vals
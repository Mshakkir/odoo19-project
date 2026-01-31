# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    # Rename the existing 'memo' field by changing its string
    # This is done in the view, not in the model

    # Add new memo field
    memo_new = fields.Text(
        string='Memo',
        help='Additional memo or notes for this payment'
    )
# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    bank_statement_id = fields.Many2one(
        'bank.statement',
        string='Bank Statement',
        copy=False,
        index=True
    )
    statement_date = fields.Date(
        string='Bank Statement Date',
        copy=False,
        help="Date when this transaction was reflected in the bank statement"
    )

    def write(self, vals):
        """Update reconciliation status based on statement_date"""
        res = super(AccountMoveLine, self).write(vals)

        # Handle reconciliation status changes
        if 'statement_date' in vals:
            for record in self:
                if vals.get('statement_date'):
                    # Mark as reconciled when statement date is set
                    if record.payment_id and record.payment_id.state == 'posted':
                        record.payment_id.write({'state': 'reconciled'})
                else:
                    # Unmark reconciliation when statement date is removed
                    if record.payment_id and record.payment_id.state == 'reconciled':
                        record.payment_id.write({'state': 'posted'})

        return res
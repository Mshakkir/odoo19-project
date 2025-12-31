# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class AccountPayment(models.Model):
    _inherit = "account.payment"

    is_bank_reconciled = fields.Boolean(
        string='Bank Reconciled',
        compute='_compute_bank_reconciled',
        store=True,
        help="Indicates if this payment is reconciled through manual bank reconciliation"
    )

    bank_reconciliation_ref = fields.Char(
        string='Bank Reconciliation Reference',
        compute='_compute_bank_reconciled',
        store=True
    )

    @api.depends('move_id.line_ids.bank_statement_id', 'move_id.line_ids.statement_date')
    def _compute_bank_reconciled(self):
        """Check if payment is bank reconciled"""
        for payment in self:
            if payment.move_id:
                reconciled_lines = payment.move_id.line_ids.filtered(
                    lambda l: l.bank_statement_id and l.statement_date
                )
                if reconciled_lines:
                    payment.is_bank_reconciled = True
                    statements = reconciled_lines.mapped('bank_statement_id.name')
                    payment.bank_reconciliation_ref = ', '.join(set(statements))
                else:
                    payment.is_bank_reconciled = False
                    payment.bank_reconciliation_ref = False
            else:
                payment.is_bank_reconciled = False
                payment.bank_reconciliation_ref = False
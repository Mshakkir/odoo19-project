# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = "account.move"

    has_manual_reconciliation = fields.Boolean(
        string='Has Manual Bank Reconciliation',
        compute='_compute_has_manual_reconciliation',
        store=True,
        help="Indicates if any line in this move is manually reconciled"
    )

    reconciliation_info = fields.Char(
        string='Reconciliation Info',
        compute='_compute_has_manual_reconciliation',
        store=True
    )

    @api.depends('line_ids.bank_statement_id', 'line_ids.statement_date')
    def _compute_has_manual_reconciliation(self):
        """Check if move has manual bank reconciliation"""
        for record in self:
            reconciled_lines = record.line_ids.filtered(
                lambda l: l.bank_statement_id and l.statement_date
            )
            if reconciled_lines:
                record.has_manual_reconciliation = True
                # Get unique statement references
                statements = reconciled_lines.mapped('bank_statement_id.name')
                record.reconciliation_info = ', '.join(set(statements))
            else:
                record.has_manual_reconciliation = False
                record.reconciliation_info = False
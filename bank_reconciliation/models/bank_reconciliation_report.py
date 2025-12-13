# -*- coding: utf-8 -*-
from odoo import models, api


class BankReconciliationReport(models.AbstractModel):
    _name = 'report.bank_reconciliation.bank_reconciliation_report_template'
    _description = 'Bank Reconciliation Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['bank.statement'].browse(docids)

        # Calculate totals and counts
        cleared_lines = docs.line_ids.filtered(lambda l: l.statement_date)
        pending_lines = docs.line_ids.filtered(lambda l: not l.statement_date)

        total_cleared = sum(cleared_lines.mapped(lambda x: x.debit - x.credit))
        total_pending = sum(pending_lines.mapped(lambda x: x.debit - x.credit))
        cleared_count = len(cleared_lines)
        pending_count = len(pending_lines)

        return {
            'doc_ids': docids,
            'doc_model': 'bank.statement',
            'docs': docs,
            'company': self.env.company,
            'total_cleared': total_cleared,
            'total_pending': total_pending,
            'cleared_count': cleared_count,
            'pending_count': pending_count,
        }
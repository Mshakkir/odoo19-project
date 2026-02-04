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

    # NEW FIELD: Add computed field to show reconciliation indicator
    is_manually_reconciled = fields.Boolean(
        string='Manually Reconciled',
        compute='_compute_is_manually_reconciled',
        store=True,
        help="Indicates if this line was reconciled through manual bank reconciliation"
    )

    reconciliation_reference = fields.Char(
        string='Reconciliation Reference',
        compute='_compute_is_manually_reconciled',
        store=True,
        help="Shows the bank reconciliation statement reference"
    )

    @api.depends('bank_statement_id', 'statement_date')
    def _compute_is_manually_reconciled(self):
        """Compute if line is manually reconciled"""
        for record in self:
            if record.bank_statement_id and record.statement_date:
                record.is_manually_reconciled = True
                record.reconciliation_reference = record.bank_statement_id.name
            else:
                record.is_manually_reconciled = False
                record.reconciliation_reference = False

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
# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class CustomBankReconcileWizard(models.TransientModel):
    """
    Bank Statement Line Reconciliation Wizard.
    Matches bank transactions with invoices, payments, or creates new entries.
    """
    _name = 'custom.bank.reconcile.wizard'
    _description = 'Bank Transaction Reconciliation Wizard'

    # ─── Statement Line Info ─────────────────────────────────────────────────
    statement_line_id = fields.Many2one(
        'account.bank.statement.line',
        string='Bank Transaction', required=True
    )
    transaction_date = fields.Date(
        related='statement_line_id.date', string='Transaction Date'
    )
    transaction_ref = fields.Char(
        related='statement_line_id.payment_ref', string='Reference'
    )
    transaction_amount = fields.Monetary(
        related='statement_line_id.amount', string='Amount',
        currency_field='currency_id'
    )
    journal_id = fields.Many2one(
        related='statement_line_id.journal_id', string='Bank Journal'
    )
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id
    )
    transaction_type = fields.Selection([
        ('credit', 'Money In (+)'),
        ('debit', 'Money Out (-)'),
    ], string='Transaction Type')

    # ─── Partner ─────────────────────────────────────────────────────────────
    partner_id = fields.Many2one('res.partner', string='Partner')

    # ─── Reconciliation Mode ─────────────────────────────────────────────────
    reconcile_mode = fields.Selection([
        ('match_invoice', 'Match with Invoice/Bill'),
        ('match_payment', 'Match with Payment'),
        ('new_entry', 'Create New Journal Entry'),
        ('writeoff', 'Write Off (Bank Charge/Fee)'),
    ], string='Reconcile As', default='match_invoice', required=True)

    # ─── Invoice / Bill Matching ─────────────────────────────────────────────
    amount = fields.Monetary(string='Amount', currency_field='currency_id')
    candidate_line_ids = fields.Many2many(
        'account.move.line',
        'custom_bank_wiz_candidate_rel',
        'wizard_id', 'line_id',
        string='Outstanding Items',
        domain=[('reconciled', '=', False), ('parent_state', '=', 'posted')]
    )
    selected_line_ids = fields.Many2many(
        'account.move.line',
        'custom_bank_wiz_selected_rel',
        'wizard_id', 'line_id',
        string='Selected to Match'
    )

    # ─── Totals ───────────────────────────────────────────────────────────────
    selected_total = fields.Monetary(
        string='Selected Total', compute='_compute_selected_total',
        currency_field='currency_id'
    )
    remaining_amount = fields.Monetary(
        string='Remaining After Match', compute='_compute_selected_total',
        currency_field='currency_id'
    )

    # ─── New Entry Mode ──────────────────────────────────────────────────────
    account_id = fields.Many2one(
        'account.account', string='Account',
        domain=[('deprecated', '=', False)]
    )
    new_entry_label = fields.Char(string='Entry Label')
    new_entry_journal_id = fields.Many2one(
        'account.journal', string='Journal',
        domain=[('type', 'in', ['general'])]
    )
    analytic_distribution = fields.Json(string='Analytic Distribution')

    # ─── Write-off Mode ──────────────────────────────────────────────────────
    writeoff_account_id = fields.Many2one(
        'account.account', string='Expense/Charge Account',
        domain=[('deprecated', '=', False)]
    )
    writeoff_label = fields.Char(
        string='Label', default='Bank Charge'
    )

    # ─── Auto-populate suggestion ────────────────────────────────────────────
    apply_rule_id = fields.Many2one(
        'custom.reconcile.model', string='Apply Rule',
        domain=[('active', '=', True)]
    )

    # ─── Computed ─────────────────────────────────────────────────────────────
    @api.depends('selected_line_ids.amount_residual', 'transaction_amount')
    def _compute_selected_total(self):
        for wiz in self:
            total = sum(abs(l.amount_residual) for l in wiz.selected_line_ids)
            wiz.selected_total = total
            wiz.remaining_amount = abs(wiz.transaction_amount or 0) - total

    @api.onchange('partner_id', 'reconcile_mode', 'transaction_type')
    def _onchange_partner_mode(self):
        """Load candidate matching lines when partner or mode changes."""
        if not self.partner_id:
            self.candidate_line_ids = False
            return

        if self.reconcile_mode in ('match_invoice', 'match_payment'):
            account_type = (
                'asset_receivable'
                if self.transaction_type == 'credit'
                else 'liability_payable'
            )
            domain = [
                ('partner_id', '=', self.partner_id.id),
                ('account_id.account_type', '=', account_type),
                ('reconciled', '=', False),
                ('parent_state', '=', 'posted'),
                ('amount_residual', '!=', 0),
            ]
            self.candidate_line_ids = [(6, 0, self.env['account.move.line'].search(
                domain, order='date asc', limit=50
            ).ids)]

    @api.onchange('apply_rule_id')
    def _onchange_apply_rule(self):
        """Auto-fill fields when a reconciliation rule is selected."""
        if not self.apply_rule_id:
            return
        rule = self.apply_rule_id
        if rule.rule_type == 'writeoff_button' and rule.line_ids:
            self.reconcile_mode = 'writeoff'
            first_line = rule.line_ids[0]
            self.writeoff_account_id = first_line.account_id
            self.writeoff_label = first_line.label or rule.name
        elif rule.rule_type == 'invoice_matching':
            self.reconcile_mode = 'match_invoice'

    def action_load_candidates(self):
        """Manually trigger loading of candidate lines."""
        self._onchange_partner_mode()
        return self._reload()

    def action_auto_match(self):
        """
        Try to auto-select lines that sum to the transaction amount.
        """
        self.ensure_one()
        target = abs(self.transaction_amount or 0)
        selected = self.env['account.move.line']
        remaining = target

        for line in self.candidate_line_ids.sorted(key=lambda l: l.date):
            if remaining <= 0.001:
                break
            residual = abs(line.amount_residual)
            if residual <= remaining + 0.01:
                selected |= line
                remaining -= residual

        self.selected_line_ids = [(6, 0, selected.ids)]
        return self._reload()

    def _reload(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'custom.bank.reconcile.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    # ─── Main Actions ─────────────────────────────────────────────────────────
    def action_validate(self):
        """
        Validate and apply the reconciliation based on selected mode.
        """
        self.ensure_one()

        if self.reconcile_mode in ('match_invoice', 'match_payment'):
            return self._reconcile_with_existing()
        elif self.reconcile_mode == 'new_entry':
            return self._reconcile_with_new_entry()
        elif self.reconcile_mode == 'writeoff':
            return self._reconcile_writeoff()

    def _reconcile_with_existing(self):
        """Match the bank transaction with selected invoice/bill/payment lines."""
        if not self.selected_line_ids:
            raise UserError(_(
                'Please select at least one invoice or payment to match with.'
            ))

        stmt_line = self.statement_line_id
        if not stmt_line:
            raise UserError(_('No bank transaction selected.'))

        # Use Odoo's built-in reconcile on the statement line
        # We link the matched move lines via the statement line's journal entry
        move_lines_to_reconcile = self.selected_line_ids

        # Try to reconcile via statement line reconciliation
        try:
            # Get the journal entry created for this statement line
            stmt_journal_entry = stmt_line.move_id
            if not stmt_journal_entry:
                raise UserError(_('The bank statement line has no associated journal entry.'))

            # Find the counterpart line in the statement journal entry
            # (the suspense/receivable/payable line)
            counterpart_account_types = ['asset_receivable', 'liability_payable',
                                          'asset_current', 'liability_current']
            stmt_counterpart_line = stmt_journal_entry.line_ids.filtered(
                lambda l: l.account_id.reconcile
            )

            if not stmt_counterpart_line:
                raise UserError(_(
                    'Cannot find a reconcilable line in the bank transaction journal entry.\n'
                    'Make sure the journal entry uses a reconcilable account.'
                ))

            # Combine and reconcile
            all_lines = stmt_counterpart_line | move_lines_to_reconcile
            all_lines.reconcile()

            # Update statement line
            stmt_line.custom_reconcile_state = 'reconciled'
            stmt_line.matched_move_line_ids = [(4, l.id) for l in move_lines_to_reconcile]

        except Exception as e:
            raise UserError(_('Reconciliation failed: %s') % str(e))

        return self._success_notification(
            _('%d item(s) matched with bank transaction.') % len(move_lines_to_reconcile)
        )

    def _reconcile_with_new_entry(self):
        """Create a new journal entry and reconcile with the bank transaction."""
        if not self.account_id:
            raise UserError(_('Please select an account for the new entry.'))

        stmt_line = self.statement_line_id
        amount = abs(self.transaction_amount or self.amount)
        label = self.new_entry_label or stmt_line.payment_ref or _('Bank Transaction')
        journal = self.new_entry_journal_id or stmt_line.journal_id

        # Build the counterpart line
        counterpart_line = {
            'account_id': self.account_id.id,
            'name': label,
            'partner_id': self.partner_id.id if self.partner_id else False,
            'debit': amount if self.transaction_type == 'credit' else 0.0,
            'credit': amount if self.transaction_type == 'debit' else 0.0,
        }

        # Only add analytic_distribution if it is set AND the field exists on move line
        if self.analytic_distribution:
            try:
                # Verify the field exists on account.move.line before using it
                self.env['account.move.line']._fields.get('analytic_distribution')
                counterpart_line['analytic_distribution'] = self.analytic_distribution
            except Exception:
                pass  # Skip analytic if not supported

        # Bank account line
        bank_line = {
            'account_id': stmt_line.journal_id.default_account_id.id,
            'name': label,
            'partner_id': self.partner_id.id if self.partner_id else False,
            'debit': amount if self.transaction_type == 'debit' else 0.0,
            'credit': amount if self.transaction_type == 'credit' else 0.0,
        }

        move_vals = {
            'move_type': 'entry',
            'journal_id': journal.id,
            'date': stmt_line.date,
            'ref': label,
            'line_ids': [(0, 0, counterpart_line), (0, 0, bank_line)],
        }

        new_move = self.env['account.move'].create(move_vals)
        new_move.action_post()

        return self._success_notification(_('New journal entry created and linked.'))

    def _reconcile_writeoff(self):
        """Write off the transaction as a bank charge or similar."""
        if not self.writeoff_account_id:
            raise UserError(_('Please select an expense account for the write-off.'))

        stmt_line = self.statement_line_id
        amount = abs(self.transaction_amount or self.amount)
        label = self.writeoff_label or _('Bank Charge')

        writeoff_move = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': stmt_line.journal_id.id,
            'date': stmt_line.date,
            'ref': label,
            'line_ids': [
                (0, 0, {
                    'account_id': self.writeoff_account_id.id,
                    'name': label,
                    'partner_id': self.partner_id.id if self.partner_id else False,
                    'debit': amount if self.transaction_type == 'debit' else 0.0,
                    'credit': amount if self.transaction_type == 'credit' else 0.0,
                }),
                (0, 0, {
                    'account_id': stmt_line.journal_id.default_account_id.id,
                    'name': label,
                    'partner_id': self.partner_id.id if self.partner_id else False,
                    'debit': amount if self.transaction_type == 'credit' else 0.0,
                    'credit': amount if self.transaction_type == 'debit' else 0.0,
                }),
            ],
        })
        writeoff_move.action_post()

        return self._success_notification(_('Transaction written off as "%s".') % label)

    def _success_notification(self, message):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Done'),
                'message': message,
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }

    def action_cancel(self):
        return {'type': 'ir.actions.act_window_close'}
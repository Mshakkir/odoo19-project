# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class CustomReconcileWizard(models.TransientModel):
    """
    Manual reconciliation wizard for journal items (Partner Reconciliation).
    Used from Accounting > Journal Items when selecting multiple lines.
    """
    _name = 'custom.reconcile.wizard'
    _description = 'Custom Manual Reconciliation Wizard'

    # ─── Header ──────────────────────────────────────────────────────────────
    partner_id = fields.Many2one('res.partner', string='Partner')
    account_id = fields.Many2one(
        'account.account', string='Account',
        domain=[('reconcile', '=', True)]
    )
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company
    )

    # ─── Lines ────────────────────────────────────────────────────────────────
    line_ids = fields.Many2many(
        'account.move.line',
        string='Journal Items to Reconcile',
        domain=[('reconciled', '=', False), ('parent_state', '=', 'posted')]
    )
    debit_move_line_ids = fields.Many2many(
        'account.move.line',
        'custom_wiz_debit_rel', 'wizard_id', 'line_id',
        string='Debit Lines',
        compute='_compute_debit_credit_lines'
    )
    credit_move_line_ids = fields.Many2many(
        'account.move.line',
        'custom_wiz_credit_rel', 'wizard_id', 'line_id',
        string='Credit Lines',
        compute='_compute_debit_credit_lines'
    )

    # ─── Totals ───────────────────────────────────────────────────────────────
    total_debit = fields.Monetary(
        string='Total Debit', compute='_compute_totals',
        currency_field='currency_id'
    )
    total_credit = fields.Monetary(
        string='Total Credit', compute='_compute_totals',
        currency_field='currency_id'
    )
    difference = fields.Monetary(
        string='Difference', compute='_compute_totals',
        currency_field='currency_id'
    )
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id
    )

    # ─── Write-off ────────────────────────────────────────────────────────────
    writeoff_is_active = fields.Boolean(
        string='Create Write-off for Difference', default=False
    )
    writeoff_account_id = fields.Many2one(
        'account.account', string='Write-off Account',
        domain=[('deprecated', '=', False)],
    )
    writeoff_journal_id = fields.Many2one(
        'account.journal', string='Write-off Journal',
        domain=[('type', 'in', ['general', 'bank', 'cash'])]
    )
    writeoff_label = fields.Char(
        string='Write-off Label', default='Write-off / Difference'
    )
    writeoff_date = fields.Date(
        string='Write-off Date', default=fields.Date.today
    )

    # ─── Computed ─────────────────────────────────────────────────────────────
    @api.depends('line_ids')
    def _compute_debit_credit_lines(self):
        for wiz in self:
            wiz.debit_move_line_ids = wiz.line_ids.filtered(lambda l: l.debit > 0)
            wiz.credit_move_line_ids = wiz.line_ids.filtered(lambda l: l.credit > 0)

    @api.depends('line_ids.debit', 'line_ids.credit')
    def _compute_totals(self):
        for wiz in self:
            wiz.total_debit = sum(wiz.line_ids.mapped('debit'))
            wiz.total_credit = sum(wiz.line_ids.mapped('credit'))
            wiz.difference = wiz.total_debit - wiz.total_credit

    @api.onchange('partner_id', 'account_id')
    def _onchange_partner_account(self):
        """When partner or account changes, reload available lines."""
        if self.partner_id and self.account_id:
            existing_ids = self.line_ids.ids
            domain = [
                ('partner_id', '=', self.partner_id.id),
                ('account_id', '=', self.account_id.id),
                ('reconciled', '=', False),
                ('parent_state', '=', 'posted'),
                ('id', 'not in', existing_ids),
            ]
            new_lines = self.env['account.move.line'].search(domain)
            self.line_ids = [(4, l.id) for l in new_lines]

    @api.constrains('writeoff_is_active', 'writeoff_account_id')
    def _check_writeoff(self):
        for wiz in self:
            if wiz.writeoff_is_active and not wiz.writeoff_account_id:
                raise ValidationError(_(
                    'Please select a Write-off Account before reconciling.'
                ))

    def action_add_outstanding_lines(self):
        """Load all outstanding lines for current partner/account."""
        self.ensure_one()
        if not self.partner_id or not self.account_id:
            raise UserError(_('Please set a Partner and Account first.'))
        domain = [
            ('partner_id', '=', self.partner_id.id),
            ('account_id', '=', self.account_id.id),
            ('reconciled', '=', False),
            ('parent_state', '=', 'posted'),
        ]
        lines = self.env['account.move.line'].search(domain, order='date asc')
        self.line_ids = [(6, 0, lines.ids)]
        return {'type': 'ir.actions.act_window_close'} if not lines else self._reload()

    def _reload(self):
        """Reload the wizard after data change."""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'custom.reconcile.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_reconcile(self):
        """
        Main reconcile action.
        - Validates lines
        - Optionally creates write-off
        - Calls reconcile()
        - Shows result
        """
        self.ensure_one()

        lines = self.line_ids
        if not lines:
            raise UserError(_('No journal items selected for reconciliation.'))
        if len(lines) < 2:
            raise UserError(_('Please select at least 2 lines to reconcile.'))

        # Check all lines belong to reconcilable accounts
        for line in lines:
            if not line.account_id.reconcile:
                raise UserError(_(
                    'Account %s does not allow reconciliation.\n'
                    'Enable "Allow Reconciliation" in the account settings.'
                ) % line.account_id.display_name)

        # Check difference
        diff = abs(self.difference)
        if diff > 0.001:
            if not self.writeoff_is_active:
                raise UserError(_(
                    'There is a difference of %.2f between debits and credits.\n'
                    'Please enable "Create Write-off" option or adjust selected lines.'
                ) % diff)
            if not self.writeoff_account_id:
                raise UserError(_('Please select a Write-off Account.'))

        # Create write-off entry if needed
        if diff > 0.001 and self.writeoff_is_active:
            writeoff_journal = self.writeoff_journal_id or lines[0].journal_id
            writeoff_move = self.env['account.move'].create({
                'move_type': 'entry',
                'journal_id': writeoff_journal.id,
                'date': self.writeoff_date or fields.Date.today(),
                'ref': self.writeoff_label or _('Write-off'),
                'line_ids': [
                    (0, 0, {
                        'account_id': lines[0].account_id.id,
                        'name': self.writeoff_label or _('Write-off'),
                        'partner_id': self.partner_id.id if self.partner_id else False,
                        'debit': diff if self.difference < 0 else 0.0,
                        'credit': diff if self.difference > 0 else 0.0,
                    }),
                    (0, 0, {
                        'account_id': self.writeoff_account_id.id,
                        'name': self.writeoff_label or _('Write-off'),
                        'partner_id': self.partner_id.id if self.partner_id else False,
                        'debit': diff if self.difference > 0 else 0.0,
                        'credit': diff if self.difference < 0 else 0.0,
                    }),
                ],
            })
            writeoff_move.action_post()

            # Add writeoff counterpart line to reconcile
            counterpart = writeoff_move.line_ids.filtered(
                lambda l: l.account_id.id == lines[0].account_id.id
            )
            lines |= counterpart

        # Perform actual reconciliation
        lines.reconcile()

        # Show success message
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Reconciliation Successful'),
                'message': _('%d journal items have been reconciled.') % len(lines),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }

    def action_cancel(self):
        """Close wizard without doing anything."""
        return {'type': 'ir.actions.act_window_close'}
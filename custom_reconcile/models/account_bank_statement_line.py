# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import re
import logging

_logger = logging.getLogger(__name__)


class AccountBankStatementLine(models.Model):
    """
    Extends bank statement lines with custom reconciliation features.
    """
    _inherit = 'account.bank.statement.line'

    # ─── Custom Fields ────────────────────────────────────────────────────────
    custom_reconcile_state = fields.Selection([
        ('open', 'Open'),
        ('matched', 'Partially Matched'),
        ('reconciled', 'Reconciled'),
    ], string='Reconcile Status', default='open', compute='_compute_custom_reconcile_state',
        store=True)

    suggested_partner_id = fields.Many2one(
        'res.partner', string='Suggested Partner',
        compute='_compute_suggested_partner', store=False
    )
    matched_move_line_ids = fields.Many2many(
        'account.move.line',
        'custom_stmt_line_move_line_rel',
        'stmt_line_id', 'move_line_id',
        string='Manually Matched Lines'
    )
    custom_writeoff_account_id = fields.Many2one(
        'account.account', string='Write-off Account',
        domain=[('deprecated', '=', False)]
    )
    custom_writeoff_label = fields.Char(
        string='Write-off Label',
        default='Bank Charges / Difference'
    )
    reconcile_model_id = fields.Many2one(
        'custom.reconcile.model', string='Applied Rule'
    )
    custom_notes = fields.Text(string='Reconciliation Notes')

    # ─── Computed ────────────────────────────────────────────────────────────
    @api.depends('is_reconciled')
    def _compute_custom_reconcile_state(self):
        for line in self:
            if line.is_reconciled:
                line.custom_reconcile_state = 'reconciled'
            elif line.matched_move_line_ids:
                line.custom_reconcile_state = 'matched'
            else:
                line.custom_reconcile_state = 'open'

    @api.depends('partner_name', 'payment_ref')
    def _compute_suggested_partner(self):
        """Auto-suggest a partner by searching partner names in the transaction."""
        for line in self:
            partner = self.env['res.partner']
            search_string = line.partner_name or line.payment_ref or ''
            if search_string:
                partner = self.env['res.partner'].search([
                    ('name', 'ilike', search_string),
                    ('active', '=', True),
                ], limit=1)
            line.suggested_partner_id = partner

    # ─── Actions ─────────────────────────────────────────────────────────────
    def action_open_reconcile_wizard(self):
        """Open the bank reconciliation wizard for this statement line."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reconcile Bank Transaction'),
            'res_model': 'custom.bank.reconcile.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_statement_line_id': self.id,
                'default_partner_id': self.partner_id.id or
                    (self.suggested_partner_id.id if self.suggested_partner_id else False),
                'default_amount': abs(self.amount),
                'default_transaction_type': 'credit' if self.amount > 0 else 'debit',
            },
        }

    def action_apply_reconcile_rules(self):
        """
        Apply custom reconciliation rules/models to this statement line.
        Tries each active rule in sequence order.
        """
        self.ensure_one()
        models = self.env['custom.reconcile.model'].search([
            ('active', '=', True),
            ('company_id', '=', self.company_id.id),
        ], order='sequence')

        for model in models:
            if self._matches_rule(model):
                self.reconcile_model_id = model
                if model.rule_type == 'writeoff_button' and model.line_ids:
                    self._apply_writeoff_rule(model)
                    return {'success': True, 'rule': model.name}
                elif model.rule_type == 'invoice_matching':
                    result = self._apply_invoice_matching(model)
                    if result:
                        return {'success': True, 'rule': model.name}
        return {'success': False}

    def _matches_rule(self, model):
        """Check if this statement line matches the given rule's criteria."""
        # Check journal
        if model.match_journal_ids and self.journal_id not in model.match_journal_ids:
            return False

        # Check amount nature
        if model.match_nature == 'amount_received' and self.amount < 0:
            return False
        if model.match_nature == 'amount_paid' and self.amount > 0:
            return False

        # Check amount range
        abs_amount = abs(self.amount)
        if model.match_amount == 'lower' and abs_amount >= model.match_amount_min:
            return False
        if model.match_amount == 'greater' and abs_amount <= model.match_amount_min:
            return False
        if model.match_amount == 'between':
            if abs_amount < model.match_amount_min or abs_amount > model.match_amount_max:
                return False

        # Check label
        label = self.payment_ref or ''
        if model.match_label == 'contains' and model.match_label_param:
            if model.match_label_param.lower() not in label.lower():
                return False
        if model.match_label == 'not_contains' and model.match_label_param:
            if model.match_label_param.lower() in label.lower():
                return False
        if model.match_label == 'match_regex' and model.match_label_param:
            try:
                if not re.search(model.match_label_param, label):
                    return False
            except re.error:
                _logger.warning('Invalid regex in reconcile model %s', model.name)
                return False

        # Check partner
        if model.match_partner and not self.partner_id:
            return False
        if model.match_partner_ids and self.partner_id not in model.match_partner_ids:
            return False

        return True

    def _apply_writeoff_rule(self, model):
        """Apply a write-off rule to this statement line."""
        if not model.line_ids:
            return
        for wline in model.line_ids:
            if wline.amount_type == 'fixed':
                amount = wline.amount
            elif wline.amount_type == 'percentage':
                amount = abs(self.amount) * (wline.amount / 100.0)
            else:
                amount = abs(self.amount)

            self.env['account.move'].create({
                'move_type': 'entry',
                'journal_id': wline.journal_id.id if wline.journal_id else self.journal_id.id,
                'date': self.date,
                'ref': wline.label or model.name,
                'line_ids': [
                    (0, 0, {
                        'account_id': wline.account_id.id,
                        'name': wline.label or model.name,
                        'debit': amount if self.amount < 0 else 0.0,
                        'credit': amount if self.amount > 0 else 0.0,
                        'partner_id': self.partner_id.id if self.partner_id else False,
                    }),
                    (0, 0, {
                        'account_id': self.journal_id.default_account_id.id,
                        'name': wline.label or model.name,
                        'debit': amount if self.amount > 0 else 0.0,
                        'credit': amount if self.amount < 0 else 0.0,
                        'partner_id': self.partner_id.id if self.partner_id else False,
                    }),
                ],
            }).action_post()

    def _apply_invoice_matching(self, model):
        """
        Find and match invoices/bills against this statement line using the rule.
        Returns True if a match was found.
        """
        if not self.partner_id:
            return False

        account_type = 'asset_receivable' if self.amount > 0 else 'liability_payable'
        domain = [
            ('partner_id', '=', self.partner_id.id),
            ('account_id.account_type', '=', account_type),
            ('reconciled', '=', False),
            ('parent_state', '=', 'posted'),
            ('amount_residual', '!=', 0),
        ]

        if model.past_months_limit > 0:
            from dateutil.relativedelta import relativedelta
            from datetime import date
            date_limit = date.today() - relativedelta(months=model.past_months_limit)
            domain.append(('date', '>=', date_limit.strftime('%Y-%m-%d')))

        order = 'date asc' if model.matching_order == 'old_first' else 'date desc'
        candidates = self.env['account.move.line'].search(domain, order=order)

        # Check tolerance
        tolerance = abs(self.amount) * (model.payment_tolerance_param / 100.0) \
            if model.allow_payment_tolerance else 0.0

        remaining = abs(self.amount)
        matched = self.env['account.move.line']

        for candidate in candidates:
            if remaining <= 0:
                break
            residual = abs(candidate.amount_residual)
            if residual <= remaining + tolerance:
                matched |= candidate
                remaining -= residual

        if matched:
            self.matched_move_line_ids = [(4, mid) for mid in matched.ids]
            return True
        return False

    @api.model
    def get_open_statement_lines(self, journal_id=None, company_id=None):
        """
        Returns all unreconciled statement lines.
        Used by the reconciliation dashboard.
        """
        domain = [('is_reconciled', '=', False)]
        if journal_id:
            domain.append(('journal_id', '=', journal_id))
        if company_id:
            domain.append(('company_id', '=', company_id))
        else:
            domain.append(('company_id', '=', self.env.company.id))

        lines = self.search(domain, order='date desc', limit=100)
        return lines.read([
            'id', 'date', 'payment_ref', 'partner_name',
            'amount', 'currency_id', 'journal_id',
            'custom_reconcile_state', 'partner_id',
        ])
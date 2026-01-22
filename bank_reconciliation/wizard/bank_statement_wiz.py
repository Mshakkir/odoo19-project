# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class BankStatement(models.Model):
    _name = 'bank.statement'
    _description = 'Bank Statement Reconciliation'
    _order = 'date_from desc, id desc'

    journal_id = fields.Many2one(
        'account.journal',
        string='Bank Journal',
        domain=[('type', '=', 'bank')],
        required=True
    )
    account_id = fields.Many2one(
        'account.account',
        string='Bank Account',
        compute='_compute_account_id',
        store=True,
        readonly=True
    )
    date_from = fields.Date(string='Date From', required=True)
    date_to = fields.Date(string='Date To', required=True)

    line_ids = fields.Many2many(
        'account.move.line',
        'bank_statement_line_rel',
        'statement_id',
        'line_id',
        string='Statement Lines'
    )

    gl_balance = fields.Monetary(
        string='Balance as per Company Books',
        readonly=True,
        compute='_compute_amount',
        store=False
    )
    bank_balance = fields.Monetary(
        string='Balance as per Bank',
        readonly=True,
        compute='_compute_amount',
        store=False
    )
    balance_difference = fields.Monetary(
        string='Amounts not Reflected in Bank',
        readonly=True,
        compute='_compute_amount',
        store=False
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        compute='_compute_currency_id',
        store=True,
        readonly=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        readonly=True
    )
    name = fields.Char(
        string='Reference',
        default='/',
        readonly=True,
        copy=False
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('cleared', 'Cleared'),
        ('overdue', 'Overdue'),
        ('done', 'Done'),
    ], string='Status', default='draft', readonly=True, tracking=True)

    @api.depends('journal_id')
    def _compute_account_id(self):
        """Compute bank account from journal"""
        for record in self:
            if record.journal_id and record.journal_id.default_account_id:
                record.account_id = record.journal_id.default_account_id
            else:
                record.account_id = False

    @api.depends('journal_id')
    def _compute_currency_id(self):
        """Compute currency from journal"""
        for record in self:
            if record.journal_id:
                record.currency_id = (
                        record.journal_id.currency_id or
                        record.journal_id.company_id.currency_id
                )
            else:
                record.currency_id = self.env.company.currency_id

    def _get_reconcile_accounts(self):
        """Get all accounts that need to be reconciled"""
        self.ensure_one()
        reconcile_accounts = [self.account_id.id] if self.account_id else []

        if not self.journal_id:
            return reconcile_accounts

        # Check if POS module is installed before trying to access POS models
        if self.env['ir.module.module'].sudo().search([
            ('name', '=', 'point_of_sale'),
            ('state', '=', 'installed')
        ], limit=1):
            # Add POS payment method accounts only if POS is installed
            if self.journal_id.type == 'bank':
                # Find POS payment methods that use this journal
                pos_payment_methods = self.env['pos.payment.method'].search([
                    '|',
                    ('journal_id', '=', self.journal_id.id),
                    ('receivable_account_id', '=', self.account_id.id)
                ])

                for method in pos_payment_methods:
                    if method.receivable_account_id and method.receivable_account_id.id not in reconcile_accounts:
                        reconcile_accounts.append(method.receivable_account_id.id)
                        _logger.info(f"Added POS payment method account: {method.receivable_account_id.name} "
                                     f"for method: {method.name}")

            # Also check for payment methods where this journal is the destination
            payment_methods = self.env['pos.payment.method'].search([
                ('journal_id', '=', self.journal_id.id)
            ])

            for method in payment_methods:
                # Add outstanding/receivable account if different
                if method.receivable_account_id and method.receivable_account_id.id not in reconcile_accounts:
                    reconcile_accounts.append(method.receivable_account_id.id)
                    _logger.info(f"Added payment method receivable account: {method.receivable_account_id.name}")

        _logger.info(f"Total reconcile accounts for {self.journal_id.name}: {len(reconcile_accounts)}")
        return reconcile_accounts

    @api.onchange('journal_id', 'date_from', 'date_to')
    def _onchange_load_lines(self):
        """Load unreconciled move lines based on journal and date range"""
        if not self.journal_id or not self.date_from or not self.date_to:
            self.line_ids = [(5, 0, 0)]
            return

        if not self.account_id:
            return {
                'warning': {
                    'title': _('Configuration Error'),
                    'message': _('Please configure a default account for this journal.')
                }
            }

        # Get all accounts that should be reconciled with this bank account
        reconcile_accounts = self._get_reconcile_accounts()

        if not reconcile_accounts:
            self.line_ids = [(5, 0, 0)]
            return {
                'warning': {
                    'title': _('No Accounts Found'),
                    'message': _('No accounts found for reconciliation.')
                }
            }

        # Build domain to include all relevant accounts
        domain = [
            ('account_id', 'in', reconcile_accounts),
            ('statement_date', '=', False),
            ('move_id.state', '=', 'posted'),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ]

        lines = self.env['account.move.line'].search(domain)

        if lines:
            self.line_ids = [(6, 0, lines.ids)]
            _logger.info(f"Loaded {len(lines)} unreconciled transactions for {self.journal_id.name}")
            _logger.info(f"Account breakdown: {lines.mapped('account_id.name')}")
        else:
            self.line_ids = [(5, 0, 0)]
            _logger.warning(f"No unreconciled transactions found for {self.journal_id.name} "
                            f"between {self.date_from} and {self.date_to}")

    @api.depends('line_ids.statement_date', 'account_id', 'date_to', 'journal_id')
    def _compute_amount(self):
        """Calculate GL balance, bank balance, and difference"""
        for record in self:
            if not record.account_id:
                record.gl_balance = 0.0
                record.bank_balance = 0.0
                record.balance_difference = 0.0
                continue

            # Get all accounts to consider
            reconcile_accounts = record._get_reconcile_accounts()

            if not reconcile_accounts:
                record.gl_balance = 0.0
                record.bank_balance = 0.0
                record.balance_difference = 0.0
                continue

            # Calculate GL balance (all posted entries up to date_to)
            domain_gl = [
                ('account_id', 'in', reconcile_accounts),
                ('move_id.state', '=', 'posted')
            ]
            if record.date_to:
                domain_gl.append(('date', '<=', record.date_to))

            gl_lines = self.env['account.move.line'].search(domain_gl)
            gl_balance = sum(line.debit - line.credit for line in gl_lines)

            # Calculate bank balance = Previously reconciled + Currently reconciled

            # 1. Get previously reconciled entries (NOT in current statement)
            domain_prev_reconciled = [
                ('account_id', 'in', reconcile_accounts),
                ('id', 'not in', record.line_ids.ids),
                ('statement_date', '!=', False),
                ('move_id.state', '=', 'posted')
            ]
            if record.date_to:
                domain_prev_reconciled.append(('statement_date', '<=', record.date_to))

            prev_reconciled_lines = self.env['account.move.line'].search(domain_prev_reconciled)
            prev_reconciled_balance = sum(line.debit - line.credit for line in prev_reconciled_lines)

            # 2. Get currently reconciled entries (IN current statement WITH statement_date)
            current_reconciled_balance = sum(
                line.debit - line.credit
                for line in record.line_ids
                if line.statement_date and line.statement_date <= (record.date_to or fields.Date.today())
            )

            # Total bank balance = previously reconciled + currently reconciled
            bank_balance = prev_reconciled_balance + current_reconciled_balance

            # Difference = Company Books - Bank Balance
            balance_difference = gl_balance - bank_balance

            # Set computed values
            record.gl_balance = gl_balance
            record.bank_balance = bank_balance
            record.balance_difference = balance_difference

            # Debug logging
            _logger.info("=" * 80)
            _logger.info(f"Bank Reconciliation Calculation - {record.name}")
            _logger.info(
                f"Accounts included: {[self.env['account.account'].browse(acc_id).name for acc_id in reconcile_accounts]}")
            _logger.info(f"GL Balance (all posted): {gl_balance}")
            _logger.info(f"Previously Reconciled: {prev_reconciled_balance}")
            _logger.info(f"Currently Reconciled: {current_reconciled_balance}")
            _logger.info(f"Bank Balance (total reconciled): {bank_balance}")
            _logger.info(f"Difference (outstanding): {balance_difference}")
            _logger.info("=" * 80)

    def action_save_reconciliation(self):
        """Save the reconciliation and mark as done"""
        self.ensure_one()

        # Link lines to this statement
        for line in self.line_ids:
            if line.statement_date:
                line.bank_statement_id = self.id

        self.write({'state': 'done'})

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Bank reconciliation saved successfully.'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_load_lines(self):
        """Manual action to reload lines"""
        self.ensure_one()
        self._onchange_load_lines()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Lines Reloaded'),
                'message': _('%d transactions loaded.') % len(self.line_ids),
                'type': 'info',
            }
        }

    def action_set_pending(self):
        """Set status to pending"""
        self.write({'state': 'pending'})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Status Changed'),
                'message': _('Reconciliation marked as pending.'),
                'type': 'info',
            }
        }

    def action_set_cleared(self):
        """Set status to cleared"""
        self.write({'state': 'cleared'})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Reconciliation marked as cleared.'),
                'type': 'success',
            }
        }

    def action_check_overdue(self):
        """Check if reconciliation is overdue (more than 7 days old)"""
        for record in self:
            if record.state in ('pending', 'draft'):
                days_old = (fields.Date.today() - record.date_to).days
                if days_old > 7:
                    record.state = 'overdue'
        return True

    @api.model
    def cron_check_overdue_reconciliations(self):
        """Cron job to automatically mark overdue reconciliations"""
        statements = self.search([('state', 'in', ['draft', 'pending'])])
        statements.action_check_overdue()
        return True

    def action_print_report(self):
        """Print PDF report for bank reconciliation statement"""
        self.ensure_one()
        return self.env.ref('bank_reconciliation.report_bank_reconciliation').report_action(self)

    def action_reopen(self):
        """Reopen a done statement for editing"""
        self.ensure_one()
        self.write({'state': 'draft'})

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Reopened'),
                'message': _('Statement reopened for editing.'),
                'type': 'warning',
            }
        }

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to generate sequence"""
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('bank.statement') or '/'

        return super(BankStatement, self).create(vals_list)

    @api.model
    def get_reconciliation_stats(self):
        """Get reconciliation statistics for dashboard"""
        return {
            'total_reconciled': self.search_count([('state', '=', 'cleared')]),
            'total_pending': self.search_count([('state', '=', 'pending')]),
            'total_overdue': self.search_count([('state', '=', 'overdue')]),
            'total_draft': self.search_count([('state', '=', 'draft')]),
        }
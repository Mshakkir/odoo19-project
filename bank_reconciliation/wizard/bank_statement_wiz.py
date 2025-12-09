# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class BankStatement(models.TransientModel):
    _name = 'bank.statement'
    _description = 'Bank Statement Reconciliation Wizard'

    journal_id = fields.Many2one(
        'account.journal',
        string='Bank Journal',
        domain=[('type', '=', 'bank')],
        required=True
    )
    account_id = fields.Many2one(
        'account.account',
        string='Bank Account',
        readonly=True
    )
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')

    statement_lines = fields.One2many(
        'bank.statement.line',
        'wizard_id',
        string="Statement Lines"
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
        readonly=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        readonly=True
    )

    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        """Set account and currency when journal changes"""
        if self.journal_id:
            self.account_id = self.journal_id.default_account_id
            self.currency_id = (
                    self.journal_id.currency_id or
                    self.journal_id.company_id.currency_id
            )
        else:
            self.account_id = False
            self.currency_id = False

    @api.onchange('journal_id', 'date_from', 'date_to')
    def _onchange_get_lines(self):
        """Load unreconciled move lines based on journal and date range"""
        if not self.journal_id:
            self.statement_lines = [(5, 0, 0)]
            return

        if not self.journal_id.default_account_id:
            raise UserError(_('Please configure a default account for this journal.'))

        # Clear existing lines
        self.statement_lines = [(5, 0, 0)]

        # Build domain for unreconciled lines
        domain = [
            ('account_id', '=', self.journal_id.default_account_id.id),
            ('statement_date', '=', False),
            ('parent_state', '=', 'posted'),
        ]

        if self.date_from:
            domain.append(('date', '>=', self.date_from))

        if self.date_to:
            domain.append(('date', '<=', self.date_to))

        # Search for matching lines
        lines = self.env['account.move.line'].search(domain, order='date desc')

        # Create wizard lines
        self.statement_lines = [
            (0, 0, {
                'move_line_id': line.id,
                'statement_date': False
            }) for line in lines
        ]

    @api.depends('statement_lines', 'statement_lines.statement_date', 'journal_id')
    def _compute_amount(self):
        """Calculate GL balance, bank balance, and difference"""
        for wizard in self:
            if not wizard.journal_id or not wizard.journal_id.default_account_id:
                wizard.gl_balance = 0.0
                wizard.bank_balance = 0.0
                wizard.balance_difference = 0.0
                continue

            account_id = wizard.journal_id.default_account_id
            currency = wizard.currency_id or wizard.company_id.currency_id

            # Determine field to use based on currency
            amount_field = 'balance' if (
                    not wizard.currency_id or
                    wizard.currency_id == wizard.company_id.currency_id
            ) else 'amount_currency'

            # Get all posted lines for this account
            domain = [
                ('account_id', '=', account_id.id),
                ('parent_state', '=', 'posted'),
            ]

            if wizard.date_to:
                domain.append(('date', '<=', wizard.date_to))

            # Calculate GL balance (all posted lines)
            all_lines = self.env['account.move.line'].search(domain)
            wizard.gl_balance = sum(all_lines.mapped(amount_field))

            # Calculate bank balance (reconciled lines only)
            reconciled_domain = domain + [('statement_date', '!=', False)]
            reconciled_lines = self.env['account.move.line'].search(reconciled_domain)
            wizard.bank_balance = sum(reconciled_lines.mapped(amount_field))

            # Calculate difference
            wizard.balance_difference = currency.round(
                wizard.gl_balance - wizard.bank_balance
            )

    def action_save_reconciliation(self):
        """Save the reconciliation statement dates"""
        self.ensure_one()

        for line in self.statement_lines:
            if line.statement_date:
                line.move_line_id.write({'statement_date': line.statement_date})

        return {'type': 'ir.actions.act_window_close'}
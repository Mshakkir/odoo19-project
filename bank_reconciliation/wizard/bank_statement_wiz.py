# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class BankStatement(models.Model):
    _name = 'bank.statement'
    _description = 'Bank Statement Reconciliation'

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
        'account.move.line',
        'bank_statement_id',
        string='Statement Lines',
        context={'tree_view_ref': 'bank_reconciliation.view_bank_statement_move_line_tree'}
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
    name = fields.Char(
        string='Reference',
        default='/',
        readonly=True,
        copy=False
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
    ], string='Status', default='draft', readonly=True)

    @api.onchange('journal_id', 'date_from', 'date_to')
    def _onchange_get_lines(self):
        """Load unreconciled move lines based on journal and date range"""
        if not self.journal_id:
            self.statement_lines = [(5, 0, 0)]  # Clear lines
            self.account_id = False
            self.currency_id = False
            return

        # Set account and currency from journal
        self.account_id = self.journal_id.default_account_id
        self.currency_id = (
                self.journal_id.currency_id or
                self.journal_id.company_id.currency_id
        )

        if not self.account_id:
            return {
                'warning': {
                    'title': _('Configuration Error'),
                    'message': _('Please configure a default account for this journal.')
                }
            }

        # Build domain for unreconciled lines
        domain = [
            ('account_id', '=', self.account_id.id),
            ('statement_date', '=', False),
            ('parent_state', '=', 'posted'),
        ]

        if self.date_from:
            domain.append(('date', '>=', self.date_from))
        if self.date_to:
            domain.append(('date', '<=', self.date_to))

        # Load lines
        lines = self.env['account.move.line'].search(domain)

        # For persistent model, we update the One2many field properly
        self.statement_lines = [(6, 0, lines.ids)]

    @api.depends('statement_lines.statement_date', 'account_id')
    def _compute_amount(self):
        """Calculate GL balance, bank balance, and difference"""
        for record in self:
            gl_balance = 0.0
            bank_balance = 0.0
            current_update = 0.0

            if not record.account_id:
                record.gl_balance = 0.0
                record.bank_balance = 0.0
                record.balance_difference = 0.0
                continue

            # Calculate GL balance (all posted entries for this account)
            domain = [
                ('account_id', '=', record.account_id.id),
                ('parent_state', '=', 'posted')
            ]
            lines = self.env['account.move.line'].search(domain)
            gl_balance = sum(line.debit - line.credit for line in lines)

            # Calculate bank balance (previously reconciled entries)
            domain = [
                ('account_id', '=', record.account_id.id),
                ('id', 'not in', record.statement_lines.ids),
                ('statement_date', '!=', False),
                ('parent_state', '=', 'posted')
            ]
            lines = self.env['account.move.line'].search(domain)
            bank_balance = sum(line.balance for line in lines)

            # Add currently updated entries
            current_update = sum(
                line.debit - line.credit
                for line in record.statement_lines
                if line.statement_date
            )

            record.gl_balance = gl_balance
            record.bank_balance = bank_balance + current_update
            record.balance_difference = record.gl_balance - record.bank_balance

    def action_save_reconciliation(self):
        """Save the reconciliation and close the wizard"""
        self.ensure_one()

        # Mark as done
        self.write({'state': 'done'})

        # Generate sequence name if not set
        if self.name == '/':
            self.name = self.env['ir.sequence'].next_by_code('bank.statement') or '/'

        return {'type': 'ir.actions.act_window_close'}

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to generate sequence"""
        # Process each dictionary in the list
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('bank.statement') or '/'

        return super(BankStatement, self).create(vals_list)
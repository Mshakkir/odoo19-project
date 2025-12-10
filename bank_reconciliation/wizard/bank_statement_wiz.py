# # -*- coding: utf-8 -*-
# from odoo import api, fields, models, _
# from odoo.exceptions import UserError
#
#
# class BankStatement(models.Model):
#     _name = 'bank.statement'
#     _description = 'Bank Statement Reconciliation'
#
#     journal_id = fields.Many2one(
#         'account.journal',
#         string='Bank Journal',
#         domain=[('type', '=', 'bank')],
#         required=True
#     )
#     account_id = fields.Many2one(
#         'account.account',
#         string='Bank Account',
#         compute='_compute_account_id',
#         store=True,
#         readonly=True
#     )
#     date_from = fields.Date(string='Date From', required=True)
#     date_to = fields.Date(string='Date To', required=True)
#
#     statement_line_ids = fields.Many2many(
#         'account.move.line',
#         'bank_statement_line_rel',
#         'statement_id',
#         'line_id',
#         string='Available Lines',
#         compute='_compute_statement_lines',
#         store=False
#     )
#
#     statement_lines = fields.One2many(
#         'account.move.line',
#         'bank_statement_id',
#         string='Statement Lines',
#         context={'tree_view_ref': 'bank_reconciliation.view_bank_statement_move_line_tree'}
#     )
#
#     gl_balance = fields.Monetary(
#         string='Balance as per Company Books',
#         readonly=True,
#         compute='_compute_amount',
#         store=False
#     )
#     bank_balance = fields.Monetary(
#         string='Balance as per Bank',
#         readonly=True,
#         compute='_compute_amount',
#         store=False
#     )
#     balance_difference = fields.Monetary(
#         string='Amounts not Reflected in Bank',
#         readonly=True,
#         compute='_compute_amount',
#         store=False
#     )
#     currency_id = fields.Many2one(
#         'res.currency',
#         string='Currency',
#         compute='_compute_currency_id',
#         store=True,
#         readonly=True
#     )
#     company_id = fields.Many2one(
#         'res.company',
#         string='Company',
#         default=lambda self: self.env.company,
#         readonly=True
#     )
#     name = fields.Char(
#         string='Reference',
#         default='/',
#         readonly=True,
#         copy=False
#     )
#     state = fields.Selection([
#         ('draft', 'Draft'),
#         ('done', 'Done'),
#     ], string='Status', default='draft', readonly=True)
#
#     @api.depends('journal_id')
#     def _compute_account_id(self):
#         """Compute bank account from journal"""
#         for record in self:
#             if record.journal_id and record.journal_id.default_account_id:
#                 record.account_id = record.journal_id.default_account_id
#             else:
#                 record.account_id = False
#
#     @api.depends('journal_id')
#     def _compute_currency_id(self):
#         """Compute currency from journal"""
#         for record in self:
#             if record.journal_id:
#                 record.currency_id = (
#                         record.journal_id.currency_id or
#                         record.journal_id.company_id.currency_id
#                 )
#             else:
#                 record.currency_id = self.env.company.currency_id
#
#     @api.depends('journal_id', 'date_from', 'date_to', 'account_id')
#     def _compute_statement_lines(self):
#         """Load unreconciled move lines based on journal and date range"""
#         for record in self:
#             if not record.journal_id or not record.account_id:
#                 record.statement_line_ids = [(5, 0, 0)]
#                 continue
#
#             # Build domain for unreconciled lines
#             domain = [
#                 ('account_id', '=', record.account_id.id),
#                 ('statement_date', '=', False),
#                 ('parent_state', '=', 'posted'),
#             ]
#
#             if record.date_from:
#                 domain.append(('date', '>=', record.date_from))
#             if record.date_to:
#                 domain.append(('date', '<=', record.date_to))
#
#             # Load lines
#             lines = self.env['account.move.line'].search(domain)
#             record.statement_line_ids = [(6, 0, lines.ids)]
#
#     @api.onchange('statement_line_ids')
#     def _onchange_statement_line_ids(self):
#         """Update statement_lines when computed lines change"""
#         if self.statement_line_ids and not self.statement_lines:
#             self.statement_lines = [(6, 0, self.statement_line_ids.ids)]
#
#     @api.depends('statement_lines.statement_date', 'account_id')
#     def _compute_amount(self):
#         """Calculate GL balance, bank balance, and difference"""
#         for record in self:
#             gl_balance = 0.0
#             bank_balance = 0.0
#             current_update = 0.0
#
#             if not record.account_id:
#                 record.gl_balance = 0.0
#                 record.bank_balance = 0.0
#                 record.balance_difference = 0.0
#                 continue
#
#             # Calculate GL balance (all posted entries for this account)
#             domain = [
#                 ('account_id', '=', record.account_id.id),
#                 ('parent_state', '=', 'posted')
#             ]
#
#             if record.date_to:
#                 domain.append(('date', '<=', record.date_to))
#
#             lines = self.env['account.move.line'].search(domain)
#             gl_balance = sum(line.debit - line.credit for line in lines)
#
#             # Calculate bank balance (previously reconciled entries)
#             domain = [
#                 ('account_id', '=', record.account_id.id),
#                 ('id', 'not in', record.statement_lines.ids),
#                 ('statement_date', '!=', False),
#                 ('parent_state', '=', 'posted')
#             ]
#
#             if record.date_to:
#                 domain.append(('statement_date', '<=', record.date_to))
#
#             lines = self.env['account.move.line'].search(domain)
#             bank_balance = sum(line.balance for line in lines)
#
#             # Add currently updated entries
#             current_update = sum(
#                 line.debit - line.credit
#                 for line in record.statement_lines
#                 if line.statement_date
#             )
#
#             record.gl_balance = gl_balance
#             record.bank_balance = bank_balance + current_update
#             record.balance_difference = record.gl_balance - record.bank_balance
#
#     def action_save_reconciliation(self):
#         """Save the reconciliation and close the wizard"""
#         self.ensure_one()
#
#         # Mark as done
#         self.write({'state': 'done'})
#
#         # Generate sequence name if not set
#         if self.name == '/':
#             self.name = self.env['ir.sequence'].next_by_code('bank.statement') or '/'
#
#         return {'type': 'ir.actions.act_window_close'}
#
#     @api.model_create_multi
#     def create(self, vals_list):
#         """Override create to generate sequence and load lines"""
#         for vals in vals_list:
#             if vals.get('name', '/') == '/':
#                 vals['name'] = self.env['ir.sequence'].next_by_code('bank.statement') or '/'
#
#         records = super(BankStatement, self).create(vals_list)
#
#         # Load statement lines after creation
#         for record in records:
#             if record.statement_line_ids and not record.statement_lines:
#                 record.statement_lines = [(6, 0, record.statement_line_ids.ids)]
#
#         return records


# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


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
        compute='_compute_account_id',
        store=True,
        readonly=True
    )
    date_from = fields.Date(string='Date From', required=True)
    date_to = fields.Date(string='Date To', required=True)

    # Use IDs field instead of One2many for better control
    line_ids = fields.Many2many(
        'account.move.line',
        'bank_statement_line_rel',
        'statement_id',
        'line_id',
        string='Statement Lines',
        domain=[('statement_date', '=', False), ('parent_state', '=', 'posted')]
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
        ('done', 'Done'),
    ], string='Status', default='draft', readonly=True)

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

        # Build domain for unreconciled lines
        domain = [
            ('account_id', '=', self.account_id.id),
            ('statement_date', '=', False),
            ('parent_state', '=', 'posted'),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ]

        _logger.info("=" * 80)
        _logger.info("BANK RECONCILIATION DEBUG INFO")
        _logger.info("=" * 80)
        _logger.info(f"Journal: {self.journal_id.name} (ID: {self.journal_id.id})")
        _logger.info(f"Account: {self.account_id.name} (ID: {self.account_id.id})")
        _logger.info(f"Date From: {self.date_from}")
        _logger.info(f"Date To: {self.date_to}")
        _logger.info(f"Search Domain: {domain}")

        # Search for ALL lines in this account first (for debugging)
        all_lines_domain = [('account_id', '=', self.account_id.id)]
        all_lines = self.env['account.move.line'].search(all_lines_domain)
        _logger.info(f"Total lines in account: {len(all_lines)}")

        # Check posted lines
        posted_domain = [
            ('account_id', '=', self.account_id.id),
            ('parent_state', '=', 'posted')
        ]
        posted_lines = self.env['account.move.line'].search(posted_domain)
        _logger.info(f"Posted lines in account: {len(posted_lines)}")

        # Check date range
        date_domain = [
            ('account_id', '=', self.account_id.id),
            ('parent_state', '=', 'posted'),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ]
        date_lines = self.env['account.move.line'].search(date_domain)
        _logger.info(f"Lines in date range: {len(date_lines)}")

        for line in date_lines[:5]:  # Show first 5
            _logger.info(f"  - Line ID {line.id}: Date={line.date}, State={line.parent_state}, "
                         f"Statement Date={line.statement_date}, Debit={line.debit}, Credit={line.credit}")

        # Search for lines with our full domain
        lines = self.env['account.move.line'].search(domain)
        _logger.info(f"Lines matching full criteria (unreconciled): {len(lines)}")
        _logger.info("=" * 80)

        if not lines:
            self.line_ids = [(5, 0, 0)]

            # Create detailed message
            msg = f'No unreconciled transactions found.\n\n'
            msg += f'Debug Info:\n'
            msg += f'- Total lines in account: {len(all_lines)}\n'
            msg += f'- Posted lines: {len(posted_lines)}\n'
            msg += f'- Lines in date range: {len(date_lines)}\n'
            msg += f'- Unreconciled lines: {len(lines)}\n\n'

            if date_lines:
                msg += 'Lines exist in date range but might be already reconciled.\n'
                msg += 'Check if statement_date is already set on these transactions.'
            elif posted_lines:
                msg += 'Posted lines exist but not in your date range.\n'
                msg += 'Try expanding your date range.'
            elif all_lines:
                msg += 'Lines exist but are not posted yet.\n'
                msg += 'Make sure to post/confirm your payments first.'
            else:
                msg += 'No transactions found in this bank account at all.\n'
                msg += 'Create some payments or journal entries first.'

            return {
                'warning': {
                    'title': _('No Transactions Found'),
                    'message': msg
                }
            }

        # Update line_ids
        self.line_ids = [(6, 0, lines.ids)]

    @api.depends('line_ids.statement_date', 'account_id', 'date_to')
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

            # Calculate GL balance (all posted entries for this account up to date_to)
            domain = [
                ('account_id', '=', record.account_id.id),
                ('parent_state', '=', 'posted')
            ]

            if record.date_to:
                domain.append(('date', '<=', record.date_to))

            lines = self.env['account.move.line'].search(domain)
            gl_balance = sum(line.debit - line.credit for line in lines)

            # Calculate bank balance (previously reconciled entries)
            domain = [
                ('account_id', '=', record.account_id.id),
                ('id', 'not in', record.line_ids.ids),
                ('statement_date', '!=', False),
                ('parent_state', '=', 'posted')
            ]

            if record.date_to:
                domain.append(('statement_date', '<=', record.date_to))

            lines = self.env['account.move.line'].search(domain)
            bank_balance = sum(line.balance for line in lines)

            # Add currently updated entries (lines in this statement that are marked)
            current_update = sum(
                line.debit - line.credit
                for line in record.line_ids
                if line.statement_date
            )

            record.gl_balance = gl_balance
            record.bank_balance = bank_balance + current_update
            record.balance_difference = record.gl_balance - record.bank_balance

    def action_save_reconciliation(self):
        """Save the reconciliation and mark as done"""
        self.ensure_one()

        # Link lines to this statement
        for line in self.line_ids:
            if line.statement_date:
                line.bank_statement_id = self.id

        self.write({'state': 'done'})
        return {'type': 'ir.actions.act_window_close'}

    def action_load_lines(self):
        """Manual action to reload lines"""
        self.ensure_one()
        self._onchange_load_lines()
        return True

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to generate sequence"""
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('bank.statement') or '/'

        return super(BankStatement, self).create(vals_list)
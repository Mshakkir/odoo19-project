# # # -*- coding: utf-8 -*-
# # from odoo import api, fields, models, _
# # from odoo.exceptions import UserError
# #
# #
# # class BankStatement(models.Model):
# #     _name = 'bank.statement'
# #     _description = 'Bank Statement Reconciliation'
# #
# #     journal_id = fields.Many2one(
# #         'account.journal',
# #         string='Bank Journal',
# #         domain=[('type', '=', 'bank')],
# #         required=True
# #     )
# #     account_id = fields.Many2one(
# #         'account.account',
# #         string='Bank Account',
# #         compute='_compute_account_id',
# #         store=True,
# #         readonly=True
# #     )
# #     date_from = fields.Date(string='Date From', required=True)
# #     date_to = fields.Date(string='Date To', required=True)
# #
# #     statement_line_ids = fields.Many2many(
# #         'account.move.line',
# #         'bank_statement_line_rel',
# #         'statement_id',
# #         'line_id',
# #         string='Available Lines',
# #         compute='_compute_statement_lines',
# #         store=False
# #     )
# #
# #     statement_lines = fields.One2many(
# #         'account.move.line',
# #         'bank_statement_id',
# #         string='Statement Lines',
# #         context={'tree_view_ref': 'bank_reconciliation.view_bank_statement_move_line_tree'}
# #     )
# #
# #     gl_balance = fields.Monetary(
# #         string='Balance as per Company Books',
# #         readonly=True,
# #         compute='_compute_amount',
# #         store=False
# #     )
# #     bank_balance = fields.Monetary(
# #         string='Balance as per Bank',
# #         readonly=True,
# #         compute='_compute_amount',
# #         store=False
# #     )
# #     balance_difference = fields.Monetary(
# #         string='Amounts not Reflected in Bank',
# #         readonly=True,
# #         compute='_compute_amount',
# #         store=False
# #     )
# #     currency_id = fields.Many2one(
# #         'res.currency',
# #         string='Currency',
# #         compute='_compute_currency_id',
# #         store=True,
# #         readonly=True
# #     )
# #     company_id = fields.Many2one(
# #         'res.company',
# #         string='Company',
# #         default=lambda self: self.env.company,
# #         readonly=True
# #     )
# #     name = fields.Char(
# #         string='Reference',
# #         default='/',
# #         readonly=True,
# #         copy=False
# #     )
# #     state = fields.Selection([
# #         ('draft', 'Draft'),
# #         ('done', 'Done'),
# #     ], string='Status', default='draft', readonly=True)
# #
# #     @api.depends('journal_id')
# #     def _compute_account_id(self):
# #         """Compute bank account from journal"""
# #         for record in self:
# #             if record.journal_id and record.journal_id.default_account_id:
# #                 record.account_id = record.journal_id.default_account_id
# #             else:
# #                 record.account_id = False
# #
# #     @api.depends('journal_id')
# #     def _compute_currency_id(self):
# #         """Compute currency from journal"""
# #         for record in self:
# #             if record.journal_id:
# #                 record.currency_id = (
# #                         record.journal_id.currency_id or
# #                         record.journal_id.company_id.currency_id
# #                 )
# #             else:
# #                 record.currency_id = self.env.company.currency_id
# #
# #     @api.depends('journal_id', 'date_from', 'date_to', 'account_id')
# #     def _compute_statement_lines(self):
# #         """Load unreconciled move lines based on journal and date range"""
# #         for record in self:
# #             if not record.journal_id or not record.account_id:
# #                 record.statement_line_ids = [(5, 0, 0)]
# #                 continue
# #
# #             # Build domain for unreconciled lines
# #             domain = [
# #                 ('account_id', '=', record.account_id.id),
# #                 ('statement_date', '=', False),
# #                 ('parent_state', '=', 'posted'),
# #             ]
# #
# #             if record.date_from:
# #                 domain.append(('date', '>=', record.date_from))
# #             if record.date_to:
# #                 domain.append(('date', '<=', record.date_to))
# #
# #             # Load lines
# #             lines = self.env['account.move.line'].search(domain)
# #             record.statement_line_ids = [(6, 0, lines.ids)]
# #
# #     @api.onchange('statement_line_ids')
# #     def _onchange_statement_line_ids(self):
# #         """Update statement_lines when computed lines change"""
# #         if self.statement_line_ids and not self.statement_lines:
# #             self.statement_lines = [(6, 0, self.statement_line_ids.ids)]
# #
# #     @api.depends('statement_lines.statement_date', 'account_id')
# #     def _compute_amount(self):
# #         """Calculate GL balance, bank balance, and difference"""
# #         for record in self:
# #             gl_balance = 0.0
# #             bank_balance = 0.0
# #             current_update = 0.0
# #
# #             if not record.account_id:
# #                 record.gl_balance = 0.0
# #                 record.bank_balance = 0.0
# #                 record.balance_difference = 0.0
# #                 continue
# #
# #             # Calculate GL balance (all posted entries for this account)
# #             domain = [
# #                 ('account_id', '=', record.account_id.id),
# #                 ('parent_state', '=', 'posted')
# #             ]
# #
# #             if record.date_to:
# #                 domain.append(('date', '<=', record.date_to))
# #
# #             lines = self.env['account.move.line'].search(domain)
# #             gl_balance = sum(line.debit - line.credit for line in lines)
# #
# #             # Calculate bank balance (previously reconciled entries)
# #             domain = [
# #                 ('account_id', '=', record.account_id.id),
# #                 ('id', 'not in', record.statement_lines.ids),
# #                 ('statement_date', '!=', False),
# #                 ('parent_state', '=', 'posted')
# #             ]
# #
# #             if record.date_to:
# #                 domain.append(('statement_date', '<=', record.date_to))
# #
# #             lines = self.env['account.move.line'].search(domain)
# #             bank_balance = sum(line.balance for line in lines)
# #
# #             # Add currently updated entries
# #             current_update = sum(
# #                 line.debit - line.credit
# #                 for line in record.statement_lines
# #                 if line.statement_date
# #             )
# #
# #             record.gl_balance = gl_balance
# #             record.bank_balance = bank_balance + current_update
# #             record.balance_difference = record.gl_balance - record.bank_balance
# #
# #     def action_save_reconciliation(self):
# #         """Save the reconciliation and close the wizard"""
# #         self.ensure_one()
# #
# #         # Mark as done
# #         self.write({'state': 'done'})
# #
# #         # Generate sequence name if not set
# #         if self.name == '/':
# #             self.name = self.env['ir.sequence'].next_by_code('bank.statement') or '/'
# #
# #         return {'type': 'ir.actions.act_window_close'}
# #
# #     @api.model_create_multi
# #     def create(self, vals_list):
# #         """Override create to generate sequence and load lines"""
# #         for vals in vals_list:
# #             if vals.get('name', '/') == '/':
# #                 vals['name'] = self.env['ir.sequence'].next_by_code('bank.statement') or '/'
# #
# #         records = super(BankStatement, self).create(vals_list)
# #
# #         # Load statement lines after creation
# #         for record in records:
# #             if record.statement_line_ids and not record.statement_lines:
# #                 record.statement_lines = [(6, 0, record.statement_line_ids.ids)]
# #
# #         return records
#
#
# # -*- coding: utf-8 -*-
# # -*- coding: utf-8 -*-
# # -*- coding: utf-8 -*-
# from odoo import api, fields, models, _
# from odoo.exceptions import UserError
# import logging
#
# _logger = logging.getLogger(__name__)
#
#
# class BankStatement(models.Model):
#     _name = 'bank.statement'
#     _description = 'Bank Statement Reconciliation'
#     _order = 'date_from desc, id desc'
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
#     line_ids = fields.Many2many(
#         'account.move.line',
#         'bank_statement_line_rel',
#         'statement_id',
#         'line_id',
#         string='Statement Lines'
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
#     @api.onchange('journal_id', 'date_from', 'date_to')
#     def _onchange_load_lines(self):
#         """Load unreconciled move lines based on journal and date range"""
#         if not self.journal_id or not self.date_from or not self.date_to:
#             self.line_ids = [(5, 0, 0)]
#             return
#
#         if not self.account_id:
#             return {
#                 'warning': {
#                     'title': _('Configuration Error'),
#                     'message': _('Please configure a default account for this journal.')
#                 }
#             }
#
#         # Build domain - Use move_id.state for Odoo 19 compatibility
#         domain = [
#             ('account_id', '=', self.account_id.id),
#             ('statement_date', '=', False),
#             ('move_id.state', '=', 'posted'),
#             ('date', '>=', self.date_from),
#             ('date', '<=', self.date_to),
#         ]
#
#         lines = self.env['account.move.line'].search(domain)
#
#         if lines:
#             self.line_ids = [(6, 0, lines.ids)]
#             _logger.info(f"Loaded {len(lines)} unreconciled transactions for {self.journal_id.name}")
#         else:
#             self.line_ids = [(5, 0, 0)]
#             _logger.warning(f"No unreconciled transactions found for {self.journal_id.name} "
#                             f"between {self.date_from} and {self.date_to}")
#
#     @api.depends('line_ids.statement_date', 'account_id', 'date_to')
#     def _compute_amount(self):
#         """Calculate GL balance, bank balance, and difference"""
#         for record in self:
#             if not record.account_id:
#                 record.gl_balance = 0.0
#                 record.bank_balance = 0.0
#                 record.balance_difference = 0.0
#                 continue
#
#             # Calculate GL balance (all posted entries up to date_to)
#             domain_gl = [
#                 ('account_id', '=', record.account_id.id),
#                 ('move_id.state', '=', 'posted')
#             ]
#             if record.date_to:
#                 domain_gl.append(('date', '<=', record.date_to))
#
#             gl_lines = self.env['account.move.line'].search(domain_gl)
#             gl_balance = sum(line.debit - line.credit for line in gl_lines)
#
#             # Calculate bank balance = Previously reconciled + Currently reconciled
#
#             # 1. Get previously reconciled entries (NOT in current statement)
#             domain_prev_reconciled = [
#                 ('account_id', '=', record.account_id.id),
#                 ('id', 'not in', record.line_ids.ids),  # Exclude current statement lines
#                 ('statement_date', '!=', False),  # Must have statement date (reconciled)
#                 ('move_id.state', '=', 'posted')
#             ]
#             if record.date_to:
#                 domain_prev_reconciled.append(('statement_date', '<=', record.date_to))
#
#             prev_reconciled_lines = self.env['account.move.line'].search(domain_prev_reconciled)
#             prev_reconciled_balance = sum(line.debit - line.credit for line in prev_reconciled_lines)
#
#             # 2. Get currently reconciled entries (IN current statement WITH statement_date)
#             current_reconciled_balance = sum(
#                 line.debit - line.credit
#                 for line in record.line_ids
#                 if line.statement_date and line.statement_date <= (record.date_to or fields.Date.today())
#             )
#
#             # Total bank balance = previously reconciled + currently reconciled
#             bank_balance = prev_reconciled_balance + current_reconciled_balance
#
#             # Difference = Company Books - Bank Balance
#             # Positive = Money in books but not in bank (deposits in transit, etc.)
#             # Negative = Money in bank but not in books (shouldn't happen normally)
#             # Or: Checks written but not cashed (outstanding checks)
#             balance_difference = gl_balance - bank_balance
#
#             # Set computed values
#             record.gl_balance = gl_balance
#             record.bank_balance = bank_balance
#             record.balance_difference = balance_difference
#
#             # Debug logging
#             _logger.info("=" * 80)
#             _logger.info(f"Bank Reconciliation Calculation - {record.name}")
#             _logger.info(f"GL Balance (all posted): {gl_balance}")
#             _logger.info(f"Previously Reconciled: {prev_reconciled_balance}")
#             _logger.info(f"Currently Reconciled: {current_reconciled_balance}")
#             _logger.info(f"Bank Balance (total reconciled): {bank_balance}")
#             _logger.info(f"Difference (outstanding): {balance_difference}")
#             _logger.info("=" * 80)
#
#     def action_save_reconciliation(self):
#         """Save the reconciliation and mark as done"""
#         self.ensure_one()
#
#         # Link lines to this statement
#         for line in self.line_ids:
#             if line.statement_date:
#                 line.bank_statement_id = self.id
#
#         self.write({'state': 'done'})
#
#         return {
#             'type': 'ir.actions.client',
#             'tag': 'display_notification',
#             'params': {
#                 'title': _('Success'),
#                 'message': _('Bank reconciliation saved successfully.'),
#                 'type': 'success',
#                 'sticky': False,
#             }
#         }
#
#     def action_load_lines(self):
#         """Manual action to reload lines"""
#         self.ensure_one()
#         self._onchange_load_lines()
#
#         return {
#             'type': 'ir.actions.client',
#             'tag': 'display_notification',
#             'params': {
#                 'title': _('Lines Reloaded'),
#                 'message': _('%d transactions loaded.') % len(self.line_ids),
#                 'type': 'info',
#             }
#         }
#
#     @api.model_create_multi
#     def create(self, vals_list):
#         """Override create to generate sequence"""
#         for vals in vals_list:
#             if vals.get('name', '/') == '/':
#                 vals['name'] = self.env['ir.sequence'].next_by_code('bank.statement') or '/'
#
#         return super(BankStatement, self).create(vals_list)
#
#     def action_reopen(self):
#         """Reopen a done statement for editing"""
#         self.ensure_one()
#         self.write({'state': 'draft'})
#
#         return {
#             'type': 'ir.actions.client',
#             'tag': 'display_notification',
#             'params': {
#                 'title': _('Reopened'),
#                 'message': _('Statement reopened for editing.'),
#                 'type': 'warning',
#             }
#         }

# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
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

        # Build domain - Use move_id.state for Odoo 19 compatibility
        domain = [
            ('account_id', '=', self.account_id.id),
            ('statement_date', '=', False),
            ('move_id.state', '=', 'posted'),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ]

        lines = self.env['account.move.line'].search(domain)

        if lines:
            self.line_ids = [(6, 0, lines.ids)]
            _logger.info(f"Loaded {len(lines)} unreconciled transactions for {self.journal_id.name}")
        else:
            self.line_ids = [(5, 0, 0)]
            _logger.warning(f"No unreconciled transactions found for {self.journal_id.name} "
                            f"between {self.date_from} and {self.date_to}")

    @api.depends('line_ids.statement_date', 'account_id', 'date_to')
    def _compute_amount(self):
        """Calculate GL balance, bank balance, and difference"""
        for record in self:
            if not record.account_id:
                record.gl_balance = 0.0
                record.bank_balance = 0.0
                record.balance_difference = 0.0
                continue

            # Calculate GL balance (all posted entries up to date_to)
            domain_gl = [
                ('account_id', '=', record.account_id.id),
                ('move_id.state', '=', 'posted')
            ]
            if record.date_to:
                domain_gl.append(('date', '<=', record.date_to))

            gl_lines = self.env['account.move.line'].search(domain_gl)
            gl_balance = sum(line.debit - line.credit for line in gl_lines)

            # 1. Get previously reconciled entries (NOT in current statement)
            domain_prev_reconciled = [
                ('account_id', '=', record.account_id.id),
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
        # Render PDF using QWeb template directly
        pdf_content, _ = self.env['ir.actions.report'].sudo()._render_qweb_pdf(
            'bank_reconciliation.bank_reconciliation_report_template',
            res_ids=[self.id]
        )

        # Return as downloadable file
        return {
            'type': 'ir.actions.act_url',
            'url': f'/report/pdf/bank_reconciliation.bank_reconciliation_report_template/{self.id}',
            'target': 'new',
        }

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
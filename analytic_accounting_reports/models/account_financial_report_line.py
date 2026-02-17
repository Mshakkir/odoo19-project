# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)


class AccountFinancialReportLine(models.Model):
    """Temporary model for displaying financial report lines (used in Balance Sheet / P&L)."""
    _name = 'account.financial.report.line'
    _description = 'Financial Report Line'
    _order = 'sequence, code'

    # -------------------------------------------------------------------------
    # Fields
    # -------------------------------------------------------------------------
    name = fields.Html(string='Account', required=True, sanitize=False)
    code = fields.Char(string='Code')
    account_id = fields.Many2one('account.account', string='Account', ondelete='cascade')
    debit = fields.Float(string='Debit', digits=(16, 2))
    credit = fields.Float(string='Credit', digits=(16, 2))
    balance = fields.Float(string='Balance', digits=(16, 2))

    report_type = fields.Selection([
        ('balance_sheet', 'Balance Sheet'),
        ('profit_loss', 'Profit & Loss')
    ], string='Report Type', default='balance_sheet')

    sequence = fields.Integer(string='Sequence', default=10)

    # Section flags (like ASSETS, LIABILITIES)
    is_section = fields.Boolean(string='Section Header', default=False)
    is_total = fields.Boolean(string='Section Total', default=False)
    account_type = fields.Selection([
        ('asset', 'Asset'),
        ('liability', 'Liability'),
        ('equity', 'Equity'),
        ('income', 'Income'),
        ('expense', 'Expense'),
        ('profit_loss', 'Profit/Loss'),
    ], string='Account Type')

    # Filter context fields
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')
    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        'account_financial_line_analytic_rel',
        'line_id',
        'analytic_id',
        string='Warehouses'
    )
    target_move = fields.Selection([
        ('posted', 'All Posted Entries'),
        ('all', 'All Entries')
    ], string='Target Moves', default='posted')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------
    def action_view_ledger(self):
        """
        Open Bills/Invoices for this account showing tax-inclusive totals (amount_total).
        - Expense/COGS accounts  → vendor bills   (in_invoice / in_refund)
        - Income accounts        → customer invoices (out_invoice / out_refund)
        Respects date range, target_move (posted/all) and analytic/warehouse filter.
        """
        self.ensure_one()

        # Ignore section headers and total rows
        if not self.account_id or self.is_section or self.is_total:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Notice',
                    'message': 'This line is a section or total, not a specific account.',
                    'type': 'warning',
                    'sticky': False,
                }
            }

        # ------------------------------------------------------------------
        # Step 1: Build account.move.line domain (for analytic matching)
        # ------------------------------------------------------------------
        aml_domain = [('account_id', '=', self.account_id.id)]

        if self.date_from:
            aml_domain.append(('date', '>=', self.date_from))
        if self.date_to:
            aml_domain.append(('date', '<=', self.date_to))
        if self.target_move == 'posted':
            aml_domain.append(('move_id.state', '=', 'posted'))

        _logger.info("=" * 80)
        _logger.info("VIEW LEDGER (Bills mode) - Account: %s %s", self.code, self.name)
        _logger.info("AML domain: %s", aml_domain)

        MoveLine = self.env['account.move.line']
        all_lines = MoveLine.search(aml_domain)
        _logger.info("Move lines before analytic filter: %d", len(all_lines))

        # ------------------------------------------------------------------
        # Step 2: Analytic / warehouse filter (JSON analytic_distribution)
        # ------------------------------------------------------------------
        if self.analytic_account_ids:
            _logger.info("Analytic filter: %s", self.analytic_account_ids.mapped('name'))
            filtered_line_ids = []
            for line in all_lines:
                if line.analytic_distribution:
                    for analytic_id in self.analytic_account_ids.ids:
                        if str(analytic_id) in line.analytic_distribution:
                            filtered_line_ids.append(line.id)
                            break
            _logger.info("Move lines after analytic filter: %d", len(filtered_line_ids))
            matching_lines = MoveLine.browse(filtered_line_ids)
        else:
            matching_lines = all_lines

        # ------------------------------------------------------------------
        # Step 3: Collect parent account.move (bill/invoice) IDs
        # ------------------------------------------------------------------
        move_ids = matching_lines.mapped('move_id').ids
        _logger.info("Matched %d journal entries (moves)", len(move_ids))

        # ------------------------------------------------------------------
        # Step 4: Determine move type from account type
        # ------------------------------------------------------------------
        account_type = self.account_id.account_type  # Odoo 17/19 field

        if account_type in ('income', 'income_other'):
            allowed_move_types = ['out_invoice', 'out_refund']
            view_label = 'Invoices'
            default_move_type = 'out_invoice'
        else:
            # Expenses, COGS, assets, liabilities → vendor bills
            allowed_move_types = ['in_invoice', 'in_refund']
            view_label = 'Bills'
            default_move_type = 'in_invoice'

        if move_ids:
            move_domain = [
                ('id', 'in', move_ids),
                ('move_type', 'in', allowed_move_types),
            ]
        else:
            move_domain = [('id', '=', False)]

        # ------------------------------------------------------------------
        # Step 5: Build window title
        # ------------------------------------------------------------------
        warehouse_info = ''
        if self.analytic_account_ids:
            warehouse_names = ', '.join(self.analytic_account_ids.mapped('name'))
            warehouse_info = f' [{warehouse_names}]'

        date_info = ''
        if self.date_from and self.date_to:
            date_info = f' ({self.date_from} to {self.date_to})'
        elif self.date_from:
            date_info = f' (From {self.date_from})'
        elif self.date_to:
            date_info = f' (To {self.date_to})'

        window_title = (
            f'{view_label} - {self.code or ""} {self.account_id.name}'
            f'{warehouse_info}{date_info}'
        )

        ctx = {
            'default_move_type': default_move_type,
            'search_default_posted': 1 if self.target_move == 'posted' else 0,
            'create': False,
        }

        _logger.info("Final move domain: %s", move_domain)
        _logger.info("Window title: %s", window_title)
        _logger.info("=" * 80)

        return {
            'name': window_title,
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': move_domain,
            'context': ctx,
            'target': 'current',
        }

    # -------------------------------------------------------------------------
    # Section Totals
    # -------------------------------------------------------------------------
    @api.model
    def create_section_totals(self, lines):
        """Insert section total lines for Assets, Liabilities, and Equity."""
        totals = {}
        result = []
        for line in lines:
            if line.account_type in ['asset', 'liability', 'equity'] and not line.is_section:
                totals.setdefault(line.account_type, {'debit': 0, 'credit': 0, 'balance': 0})
                totals[line.account_type]['debit'] += line.debit
                totals[line.account_type]['credit'] += line.credit
                totals[line.account_type]['balance'] += line.balance
            result.append(line)

        for acc_type, vals in totals.items():
            result.append(self.create({
                'name': f"<b>Total {acc_type.capitalize()}</b>",
                'is_total': True,
                'is_section': False,
                'account_type': acc_type,
                'debit': vals['debit'],
                'credit': vals['credit'],
                'balance': vals['balance'],
                'sequence': 9999,
            }))
        return result

    # -------------------------------------------------------------------------
    # Maintenance (optional cron)
    # -------------------------------------------------------------------------
    @api.model
    def cleanup_old_lines(self):
        """Automatically delete temporary report lines older than 1 day."""
        try:
            old_date = fields.Datetime.now() - timedelta(days=1)
            old_lines = self.search([('create_date', '<', old_date)])
            if old_lines:
                _logger.info("🧹 Cleaning up %d old financial report lines...", len(old_lines))
                old_lines.unlink()
            else:
                _logger.info("✅ No old financial report lines found to clean up.")
        except Exception as e:
            _logger.exception("Error during cleanup_old_lines: %s", e)











# # -*- coding: utf-8 -*-
# from datetime import timedelta
# from odoo import api, fields, models
# import logging
#
# _logger = logging.getLogger(__name__)
#
#
# class AccountFinancialReportLine(models.Model):
#     """Temporary model for displaying financial report lines (used in Balance Sheet / P&L)."""
#     _name = 'account.financial.report.line'
#     _description = 'Financial Report Line'
#     _order = 'sequence, code'
#
#     # -------------------------------------------------------------------------
#     # Fields
#     # -------------------------------------------------------------------------
#     name = fields.Html(string='Account', required=True, sanitize=False)
#     code = fields.Char(string='Code')
#     account_id = fields.Many2one('account.account', string='Account', ondelete='cascade')
#     debit = fields.Float(string='Debit', digits=(16, 2))
#     credit = fields.Float(string='Credit', digits=(16, 2))
#     balance = fields.Float(string='Balance', digits=(16, 2))
#
#     report_type = fields.Selection([
#         ('balance_sheet', 'Balance Sheet'),
#         ('profit_loss', 'Profit & Loss')
#     ], string='Report Type', default='balance_sheet')
#
#     sequence = fields.Integer(string='Sequence', default=10)
#
#     # Section flags (like ASSETS, LIABILITIES)
#     is_section = fields.Boolean(string='Section Header', default=False)
#     is_total = fields.Boolean(string='Section Total', default=False)
#     account_type = fields.Selection([
#         ('asset', 'Asset'),
#         ('liability', 'Liability'),
#         ('equity', 'Equity'),
#         ('income', 'Income'),
#         ('expense', 'Expense'),
#         ('profit_loss', 'Profit/Loss'),
#     ], string='Account Type')
#
#     # Filter context fields
#     date_from = fields.Date(string='Date From')
#     date_to = fields.Date(string='Date To')
#     analytic_account_ids = fields.Many2many(
#         'account.analytic.account',
#         'account_financial_line_analytic_rel',
#         'line_id',
#         'analytic_id',
#         string='Warehouses'
#     )
#     target_move = fields.Selection([
#         ('posted', 'All Posted Entries'),
#         ('all', 'All Entries')
#     ], string='Target Moves', default='posted')
#     company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
#
#     # -------------------------------------------------------------------------
#     # Actions
#     # -------------------------------------------------------------------------
#     def action_view_ledger(self):
#         """Open General Ledger view for this account with applied filters."""
#         self.ensure_one()
#
#         # Ignore non-account lines
#         if not self.account_id or self.is_section or self.is_total:
#             return {
#                 'type': 'ir.actions.client',
#                 'tag': 'display_notification',
#                 'params': {
#                     'title': 'Notice',
#                     'message': 'This line is a section or total, not a specific account.',
#                     'type': 'warning',
#                     'sticky': False,
#                 }
#             }
#
#         domain = [('account_id', '=', self.account_id.id)]
#
#         # Date filters
#         if self.date_from:
#             domain.append(('date', '>=', self.date_from))
#         if self.date_to:
#             domain.append(('date', '<=', self.date_to))
#         if self.target_move == 'posted':
#             domain.append(('move_id.state', '=', 'posted'))
#
#         # ✅ FIXED: Handle analytic_distribution JSON properly
#         if self.analytic_account_ids:
#             # Get all move lines for this account first (with date/state filters)
#             MoveLine = self.env['account.move.line']
#             all_lines = MoveLine.search(domain)
#
#             _logger.info("=" * 80)
#             _logger.info("🔍 DEBUGGING ANALYTIC FILTER")
#             _logger.info("Account: %s - %s", self.code, self.name)
#             _logger.info("Selected Analytics: %s", self.analytic_account_ids.mapped('name'))
#             _logger.info("Selected Analytic IDs: %s", self.analytic_account_ids.ids)
#             _logger.info("Total lines before analytic filter: %d", len(all_lines))
#
#             # Filter by analytic accounts manually
#             filtered_line_ids = []
#             for line in all_lines:
#                 if line.analytic_distribution:
#                     _logger.info("Line ID %d - Analytic Distribution: %s", line.id, line.analytic_distribution)
#                     # Check if any of our selected analytics are in this line's distribution
#                     for analytic_id in self.analytic_account_ids.ids:
#                         if str(analytic_id) in line.analytic_distribution:
#                             filtered_line_ids.append(line.id)
#                             _logger.info("  ✅ MATCH: Line %d contains analytic %d", line.id, analytic_id)
#                             break
#                 else:
#                     _logger.info("Line ID %d - No analytic distribution", line.id)
#
#             _logger.info("Filtered line IDs: %s", filtered_line_ids)
#             _logger.info("Total lines after analytic filter: %d", len(filtered_line_ids))
#             _logger.info("=" * 80)
#
#             # Update domain to only include filtered lines
#             if filtered_line_ids:
#                 domain = [('id', 'in', filtered_line_ids)]
#             else:
#                 # No lines match - return empty domain
#                 domain = [('id', '=', False)]
#
#         ctx = dict(self.env.context or {})
#         ctx.update({
#             'search_default_posted': 1 if self.target_move == 'posted' else 0,
#             'default_account_id': self.account_id.id,
#         })
#
#         # Label information
#         warehouse_info = ''
#         if self.analytic_account_ids:
#             warehouse_names = ', '.join(self.analytic_account_ids.mapped('name'))
#             warehouse_info = f' - {warehouse_names}'
#
#         date_info = ''
#         if self.date_from and self.date_to:
#             date_info = f' ({self.date_from} to {self.date_to})'
#         elif self.date_from:
#             date_info = f' (From {self.date_from})'
#         elif self.date_to:
#             date_info = f' (To {self.date_to})'
#
#         _logger.info("=" * 80)
#         _logger.info("VIEW LEDGER - Account: %s %s", self.code, self.name)
#         _logger.info("Final Domain: %s", domain)
#         _logger.info("Context: %s", ctx)
#         _logger.info("=" * 80)
#
#         return {
#             'name': f'Ledger - {self.code or ""} {self.name}{warehouse_info}{date_info}',
#             'type': 'ir.actions.act_window',
#             'res_model': 'account.move.line',
#             'view_mode': 'list,form',
#             'domain': domain,
#             'context': ctx,
#             'target': 'current',
#         }
#
#     # -------------------------------------------------------------------------
#     # Section Totals
#     # -------------------------------------------------------------------------
#     @api.model
#     def create_section_totals(self, lines):
#         """Insert section total lines for Assets, Liabilities, and Equity."""
#         totals = {}
#         result = []
#         for line in lines:
#             if line.account_type in ['asset', 'liability', 'equity'] and not line.is_section:
#                 totals.setdefault(line.account_type, {'debit': 0, 'credit': 0, 'balance': 0})
#                 totals[line.account_type]['debit'] += line.debit
#                 totals[line.account_type]['credit'] += line.credit
#                 totals[line.account_type]['balance'] += line.balance
#             result.append(line)
#
#         for acc_type, vals in totals.items():
#             result.append(self.create({
#                 'name': f"<b>Total {acc_type.capitalize()}</b>",
#                 'is_total': True,
#                 'is_section': False,
#                 'account_type': acc_type,
#                 'debit': vals['debit'],
#                 'credit': vals['credit'],
#                 'balance': vals['balance'],
#                 'sequence': 9999,
#             }))
#         return result
#
#     # -------------------------------------------------------------------------
#     # Maintenance (optional cron)
#     # -------------------------------------------------------------------------
#     @api.model
#     def cleanup_old_lines(self):
#         """Automatically delete temporary report lines older than 1 day."""
#         try:
#             old_date = fields.Datetime.now() - timedelta(days=1)
#             old_lines = self.search([('create_date', '<', old_date)])
#             if old_lines:
#                 _logger.info("🧹 Cleaning up %d old financial report lines...", len(old_lines))
#                 old_lines.unlink()
#             else:
#                 _logger.info("✅ No old financial report lines found to clean up.")
#         except Exception as e:
#             _logger.exception("Error during cleanup_old_lines: %s", e)

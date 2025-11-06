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
        """Open General Ledger view for this account with applied filters."""
        self.ensure_one()

        # Ignore non-account lines
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

        domain = [('account_id', '=', self.account_id.id)]

        # Date filters
        if self.date_from:
            domain.append(('date', '>=', self.date_from))
        if self.date_to:
            domain.append(('date', '<=', self.date_to))
        if self.target_move == 'posted':
            domain.append(('move_id.state', '=', 'posted'))

        if self.analytic_account_ids:
            analytic_domain_parts = []
            for analytic in self.analytic_account_ids:
                # ✅ Correct JSON domain search (works for single or multiple analytics)
                analytic_domain_parts.append(('analytic_distribution', 'contains', {str(analytic.id): 0.0}))

            if len(analytic_domain_parts) > 1:
                or_operator = ['|'] * (len(analytic_domain_parts) - 1)
                domain = domain + or_operator + analytic_domain_parts
            else:
                domain.extend(analytic_domain_parts)

        # # ✅ FIXED: Only use analytic_distribution JSON field (modern Odoo)
        # if self.analytic_account_ids:
        #     analytic_domain_parts = []
        #     for analytic in self.analytic_account_ids:
        #         analytic_domain_parts.append(('analytic_distribution', 'ilike', f'"{analytic.id}"'))
        #
        #     # Build OR chain for multiple analytics
        #     if len(analytic_domain_parts) > 1:
        #         or_operator = ['|'] * (len(analytic_domain_parts) - 1)
        #         domain = domain + or_operator + analytic_domain_parts
        #     else:
        #         domain.extend(analytic_domain_parts)

        ctx = dict(self.env.context or {})
        ctx.update({
            'search_default_posted': 1 if self.target_move == 'posted' else 0,
            'default_account_id': self.account_id.id,
        })

        # Label information
        warehouse_info = ''
        if self.analytic_account_ids:
            warehouse_names = ', '.join(self.analytic_account_ids.mapped('name'))
            warehouse_info = f' - {warehouse_names}'

        date_info = ''
        if self.date_from and self.date_to:
            date_info = f' ({self.date_from} to {self.date_to})'
        elif self.date_from:
            date_info = f' (From {self.date_from})'
        elif self.date_to:
            date_info = f' (To {self.date_to})'

        _logger.info("=" * 80)
        _logger.info("VIEW LEDGER - Account: %s %s", self.code, self.name)
        _logger.info("Domain: %s", domain)
        _logger.info("Context: %s", ctx)
        _logger.info("=" * 80)

        return {
            'name': f'Ledger - {self.code or ""} {self.name}{warehouse_info}{date_info}',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'list,form',
            'domain': domain,
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
# import logging
# from odoo import api, fields, models
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
#     name = fields.Char(string='Account', required=True)
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
#     # 🔹 Added field for section header (Assets / Liabilities / Profit Loss)
#     is_section = fields.Boolean(string='Section Header', default=False,
#                                 help="If true, this line is used as a section header (e.g. Assets, Liabilities).")
#
#     # 🔹 Optional: categorize accounts for grouping
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
#         if not self.account_id:
#             return {
#                 'type': 'ir.actions.client',
#                 'tag': 'display_notification',
#                 'params': {
#                     'title': 'Warning',
#                     'message': 'No account linked to this line.',
#                     'type': 'warning',
#                     'sticky': False,
#                 }
#             }
#
#         # Domain setup
#         domain = [('account_id', '=', self.account_id.id)]
#
#         if self.date_from:
#             domain.append(('date', '>=', self.date_from))
#         if self.date_to:
#             domain.append(('date', '<=', self.date_to))
#         if self.target_move == 'posted':
#             domain.append(('move_id.state', '=', 'posted'))
#
#         # Analytic filter (warehouse)
#         if self.analytic_account_ids:
#             analytic_domain = []
#             for analytic in self.analytic_account_ids:
#                 analytic_domain.append(('analytic_distribution', 'ilike', f'"{analytic.id}"'))
#             # Combine with OR
#             if len(analytic_domain) > 1:
#                 domain.append('|' * (len(analytic_domain) - 1))
#             domain.extend(analytic_domain)
#
#         # Context
#         ctx = dict(self.env.context or {})
#         ctx.update({
#             'search_default_posted': 1 if self.target_move == 'posted' else 0,
#             'default_account_id': self.account_id.id,
#         })
#
#         # Title formatting
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
#         _logger.info("Domain: %s", domain)
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

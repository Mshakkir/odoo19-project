# -*- coding: utf-8 -*-
from odoo import api, fields, models
from collections import OrderedDict
import logging

_logger = logging.getLogger(__name__)


class AccountingReport(models.TransientModel):
    _inherit = "accounting.report"

    # -----------------------------
    # Analytic filter fields
    # -----------------------------
    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        string="Warehouses",
        help=(
            "Select specific warehouses/analytic accounts for filtering.\n"
            "• Leave empty: Show all warehouses combined\n"
            "• Select ONE: Show only that warehouse (separate report)\n"
            "• Select MULTIPLE: Show combined with optional breakdown"
        )
    )

    include_combined = fields.Boolean(
        string='Show Combined Column',
        default=False,
        help='Show a combined total column when multiple analytic accounts are selected.'
    )

    warehouse_selection_info = fields.Html(
        string='Selection Info',
        compute='_compute_warehouse_info',
        store=False
    )

    # -----------------------------
    # Computed fields
    # -----------------------------
    @api.depends('analytic_account_ids')
    def _compute_warehouse_info(self):
        for record in self:
            count = len(record.analytic_account_ids)
            if count == 0:
                info = '<span style="color:#0066cc;">📊 Will show <b>ALL WAREHOUSES COMBINED</b></span>'
            elif count == 1:
                name = record.analytic_account_ids[0].name
                info = f'<span style="color:#28a745;">📋 Will show <b>{name} ONLY</b> (Separate Report)</span>'
            else:
                info = (
                    f'<span style="color:#ff6600;">📦 Will show <b>{count} WAREHOUSES COMBINED</b> '
                    f'(with optional breakdown)</span>'
                )
            record.warehouse_selection_info = info

    @api.onchange('analytic_account_ids')
    def _onchange_analytic_account_ids(self):
        if len(self.analytic_account_ids) <= 1:
            self.include_combined = False

    # -----------------------------
    # Context Builders - FIXED
    # -----------------------------
    def _build_contexts(self, data):
        """Override to include analytic account IDs in context"""

        analytic_ids = []
        form_data = data.get('form', {})

        _logger.info("=" * 80)
        _logger.info("🔧 _build_contexts called")
        _logger.info("Form data keys: %s", form_data.keys())

        # CRITICAL FIX: Ensure company_id is present before calling parent
        if 'company_id' not in form_data:
            company = self.company_id if self.company_id else self.env.company
            form_data['company_id'] = [company.id, company.name]
            _logger.info("Added missing company_id: %s", form_data['company_id'])

        # Now safe to call parent
        result = super()._build_contexts(data)

        # Extract analytic data
        analytic_data = form_data.get('analytic_account_ids', [])
        _logger.info("Analytic data raw: %s", analytic_data)

        if analytic_data:
            if isinstance(analytic_data, (list, tuple)) and len(analytic_data) > 0:
                if isinstance(analytic_data[0], (list, tuple)) and len(analytic_data[0]) > 2:
                    # Format: [(6, 0, [ids])]
                    analytic_ids = analytic_data[0][2]
                else:
                    # Format: [id1, id2, ...]
                    analytic_ids = list(analytic_data)

        _logger.info("Extracted analytic_ids: %s", analytic_ids)

        # CRITICAL: Add to context
        result['analytic_account_ids'] = analytic_ids
        result['include_combined'] = form_data.get('include_combined', False)

        _logger.info("Final context: %s", result)
        _logger.info("=" * 80)

        return result

    def _build_comparison_context(self, data):
        """Override to include analytic account IDs in comparison context"""

        form_data = data.get('form', {})

        # CRITICAL FIX: Ensure company_id is present before calling parent
        if 'company_id' not in form_data:
            company = self.company_id if self.company_id else self.env.company
            form_data['company_id'] = [company.id, company.name]

        result = super()._build_comparison_context(data)

        analytic_ids = []
        analytic_data = form_data.get('analytic_account_ids', [])

        if analytic_data:
            if isinstance(analytic_data, (list, tuple)) and len(analytic_data) > 0:
                if isinstance(analytic_data[0], (list, tuple)) and len(analytic_data[0]) > 2:
                    analytic_ids = analytic_data[0][2]
                else:
                    analytic_ids = list(analytic_data)

        result['analytic_account_ids'] = analytic_ids
        result['include_combined'] = form_data.get('include_combined', False)

        return result

    # -----------------------------
    # Override check_report to ensure context is passed
    # -----------------------------
    def check_report(self):
        """Override to ensure analytic context is properly set before generating report"""
        self.ensure_one()

        _logger.info("=" * 80)
        _logger.info("🖨️ CHECK_REPORT (Print Button) called")
        _logger.info("Selected analytic accounts: %s", self.analytic_account_ids.ids)
        _logger.info("Analytic names: %s", self.analytic_account_ids.mapped('name'))
        _logger.info("=" * 80)

        # Get the data dictionary with ALL required fields
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')

        # Read ALL fields that parent module expects
        data['form'] = self.read([
            'date_from', 'date_to', 'journal_ids', 'target_move',
            'company_id',  # CRITICAL: Parent module needs this
            'analytic_account_ids', 'include_combined'
        ])[0]

        # Ensure used_context is built with analytic IDs
        used_context = self._build_contexts(data)
        data['form']['used_context'] = used_context

        _logger.info("Data being passed to report: %s", data)
        _logger.info("Used context: %s", used_context)

        # Call parent with updated context
        return super(AccountingReport, self.with_context(**used_context)).check_report()

    # -----------------------------
    # Main Report Action
    # -----------------------------
    def action_view_details(self):
        """
        Build view details for Balance Sheet or Profit & Loss.
        - Shows only non-zero accounts
        - Shows Income & Expense as positive
        - Places Net Profit/Loss immediately after the last Equity account
        """
        self.ensure_one()
        report_type = 'balance_sheet'
        if self.account_report_id and 'loss' in self.account_report_id.name.lower():
            report_type = 'profit_loss'

        # Clear old temporary lines
        self.env['account.financial.report.line'].search([]).unlink()

        ctx = self._build_contexts({'form': self.read()[0]})
        analytic_ids = ctx.get('analytic_account_ids', [])
        date_from = ctx.get('date_from')
        date_to = ctx.get('date_to')
        target_move = ctx.get('target_move', 'posted')

        _logger.info("=" * 80)
        _logger.info("📊 ACTION_VIEW_DETAILS (Show Details) called")
        _logger.info("Report type: %s", report_type)
        _logger.info("Context analytic_ids: %s", analytic_ids)
        _logger.info("Full context: %s", ctx)
        _logger.info("=" * 80)

        # Account groups (ordered)
        if report_type == 'balance_sheet':
            group_mapping = OrderedDict([
                ('ASSETS', [
                    'asset_receivable', 'asset_bank', 'asset_cash',
                    'asset_current', 'asset_non_current',
                    'asset_prepayments', 'asset_fixed'
                ]),
                ('LIABILITIES', [
                    'liability_payable', 'liability_credit_card',
                    'liability_current', 'liability_non_current'
                ]),
                ('EQUITY', [
                    'equity', 'equity_current_earnings'
                ]),
            ])
        else:
            group_mapping = OrderedDict([
                ('INCOME', [
                    'income', 'other_income'
                ]),
                ('EXPENSES', [
                    'expense', 'other_expense', 'depreciation',
                    'expense_direct_cost', 'expense_cost_of_revenue'
                ]),
            ])

        ReportLine = self.env['account.financial.report.line']
        FinancialReport = self.env['report.accounting_pdf_reports.report_financial']

        sequence = 1
        group_totals = {}
        equity_last_account_seq = None

        # Build sections and account lines
        for group_name, account_types in group_mapping.items():
            accounts = self.env['account.account'].search([('account_type', 'in', account_types)])
            if not accounts:
                continue

            balances = FinancialReport.with_context(ctx)._compute_account_balance(accounts)
            total_balance = total_debit = total_credit = 0.0

            # Create section header
            section = ReportLine.create({
                'name': f"<b>{group_name}</b>",
                'is_section': True,
                'sequence': sequence,
                'report_type': report_type,
                'date_from': date_from,
                'date_to': date_to,
                'target_move': target_move,
                'analytic_account_ids': [(6, 0, analytic_ids)],
            })
            sequence += 1

            # Create account lines
            for acc in accounts:
                vals = balances.get(acc.id)
                if not vals:
                    continue

                balance = abs(vals.get('balance', 0.0))
                debit = vals.get('debit', 0.0)
                credit = vals.get('credit', 0.0)

                if abs(balance) < 0.0001 and abs(debit) < 0.0001 and abs(credit) < 0.0001:
                    continue

                total_balance += balance
                total_debit += debit
                total_credit += credit

                ReportLine.create({
                    'name': acc.name,
                    'code': acc.code,
                    'account_id': acc.id,
                    'debit': debit,
                    'credit': credit,
                    'balance': balance,
                    'report_type': report_type,
                    'sequence': sequence,
                    'date_from': date_from,
                    'date_to': date_to,
                    'target_move': target_move,
                    'analytic_account_ids': [(6, 0, analytic_ids)],
                })

                if group_name == 'EQUITY':
                    equity_last_account_seq = sequence

                sequence += 1

            section.write({
                'debit': total_debit,
                'credit': total_credit,
                'balance': total_balance,
            })

            group_totals[group_name] = total_balance
            sequence += 1

        # Net Profit / Net Loss
        if report_type == 'profit_loss':
            income_total = group_totals.get('INCOME', 0.0)
            expense_total = group_totals.get('EXPENSES', 0.0)
            net = income_total - expense_total
        else:
            income_accounts = self.env['account.account'].search([
                ('account_type', 'in', ['income', 'other_income'])
            ])
            expense_accounts = self.env['account.account'].search([
                ('account_type', 'in', ['expense', 'other_expense', 'depreciation',
                                        'expense_direct_cost', 'expense_cost_of_revenue'])
            ])

            inc_bal = sum(v.get('balance', 0.0) for v in
                          FinancialReport.with_context(ctx)._compute_account_balance(income_accounts).values())
            exp_bal = sum(v.get('balance', 0.0) for v in
                          FinancialReport.with_context(ctx)._compute_account_balance(expense_accounts).values())

            net = abs(inc_bal) - abs(exp_bal)

        label = "<b>Net Profit</b>" if net > 0 else "<b>Net Loss</b>"
        display_value = abs(net)

        if report_type == 'balance_sheet' and equity_last_account_seq:
            insert_sequence = equity_last_account_seq + 1
        else:
            insert_sequence = sequence + 1

        ReportLine.create({
            'name': label,
            'is_total': True,
            'report_type': report_type,
            'balance': display_value,
            'sequence': insert_sequence,
            'date_from': date_from,
            'date_to': date_to,
            'target_move': target_move,
            'analytic_account_ids': [(6, 0, analytic_ids)],
        })

        return {
            'type': 'ir.actions.act_window',
            'name': f'{self.account_report_id.name} Details',
            'res_model': 'account.financial.report.line',
            'view_mode': 'list',
            'target': 'current',
            'domain': [('report_type', '=', report_type)],
            'context': ctx,
        }

# # -*- coding: utf-8 -*-
# from odoo import api, fields, models
#
#
# class AccountingReport(models.TransientModel):
#     _inherit = "accounting.report"
#
#     # Analytic filter fields
#     analytic_account_ids = fields.Many2many(
#         'account.analytic.account',
#         string="",
#         help=(
#             "Select specific warehouses/analytic accounts for filtering.\n"
#             "• Leave empty: Show all warehouses combined\n"
#             "• Select ONE: Show only that warehouse (separate report)\n"
#             "• Select MULTIPLE: Show combined with optional breakdown"
#         )
#     )
#
#     include_combined = fields.Boolean(
#         string='Show Combined Column',
#         default=False,
#         help='Show a combined total column when multiple analytic accounts are selected.'
#     )
#
#     warehouse_selection_info = fields.Html(
#         string='Selection Info',
#         compute='_compute_warehouse_info',
#         store=False
#     )
#
#     # -----------------------------
#     # Computed fields
#     # -----------------------------
#     @api.depends('analytic_account_ids')
#     def _compute_warehouse_info(self):
#         """Show helpful info about what report will be generated"""
#         for record in self:
#             count = len(record.analytic_account_ids)
#             if count == 0:
#                 info = '<span style="color:#0066cc;">📊 Will show <b>ALL WAREHOUSES COMBINED</b></span>'
#             elif count == 1:
#                 name = record.analytic_account_ids[0].name
#                 info = f'<span style="color:#28a745;">📋 Will show <b>{name} ONLY</b> (Separate Report)</span>'
#             else:
#                 info = (
#                     f'<span style="color:#ff6600;">📦 Will show <b>{count} WAREHOUSES COMBINED</b> '
#                     f'(with optional breakdown)</span>'
#                 )
#             record.warehouse_selection_info = info
#
#     # -----------------------------
#     # Onchange methods
#     # -----------------------------
#     @api.onchange('analytic_account_ids')
#     def _onchange_analytic_account_ids(self):
#         """Auto-disable combined column when only one analytic is selected"""
#         if len(self.analytic_account_ids) <= 1:
#             self.include_combined = False
#
#     # -----------------------------
#     # Context builders
#     # -----------------------------
#     def _build_contexts(self, data):
#         """Override to add analytic account context"""
#         result = super()._build_contexts(data)
#
#         analytic_ids = []
#         form_data = data.get('form', {})
#         analytic_data = form_data.get('analytic_account_ids', [])
#
#         # Handle different formats of many2many field
#         if analytic_data:
#             if isinstance(analytic_data, (list, tuple)) and analytic_data:
#                 if isinstance(analytic_data[0], (list, tuple)):
#                     # Format: [(6, 0, [ids])]
#                     analytic_ids = analytic_data[0][2] if len(analytic_data[0]) > 2 else []
#                 else:
#                     # Format: [id1, id2, ...]
#                     analytic_ids = list(analytic_data)
#
#         result['analytic_account_ids'] = analytic_ids
#         result['include_combined'] = form_data.get('include_combined', False)
#         return result
#
#     def _build_comparison_context(self, data):
#         """Override to add analytic account context for comparison"""
#         result = super()._build_comparison_context(data)
#
#         analytic_ids = []
#         form_data = data.get('form', {})
#         analytic_data = form_data.get('analytic_account_ids', [])
#
#         if analytic_data:
#             if isinstance(analytic_data, (list, tuple)) and analytic_data:
#                 if isinstance(analytic_data[0], (list, tuple)):
#                     analytic_ids = analytic_data[0][2] if len(analytic_data[0]) > 2 else []
#                 else:
#                     analytic_ids = list(analytic_data)
#
#         result['analytic_account_ids'] = analytic_ids
#         result['include_combined'] = form_data.get('include_combined', False)
#         return result
#
#     # -----------------------------
#     # Main report action
#     # -----------------------------
#     def check_report(self):
#         """Override to inject analytic data into the report"""
#         self.ensure_one()
#
#         parent_fields = [
#             'date_from_cmp', 'debit_credit', 'date_to_cmp',
#             'filter_cmp', 'account_report_id', 'enable_filter',
#             'label_filter', 'target_move', 'date_from', 'date_to',
#             'journal_ids', 'company_id'
#         ]
#
#         all_fields = parent_fields + ['analytic_account_ids', 'include_combined']
#
#         data = {
#             'ids': self.env.context.get('active_ids', []),
#             'model': self.env.context.get('active_model', 'ir.ui.menu'),
#         }
#
#         form_data = self.read(all_fields)[0]
#         data['form'] = form_data
#
#         # Ensure analytic_account_ids is in proper format
#         if self.analytic_account_ids:
#             data['form']['analytic_account_ids'] = [(6, 0, self.analytic_account_ids.ids)]
#         else:
#             data['form']['analytic_account_ids'] = []
#
#         data['form']['include_combined'] = self.include_combined
#
#         # Clean tuple date fields
#         for field in ['date_from_cmp', 'date_to_cmp', 'date_from', 'date_to']:
#             if field in data['form'] and data['form'][field]:
#                 if isinstance(data['form'][field], tuple):
#                     data['form'][field] = data['form'][field][0]
#
#         used_context = self._build_contexts(data)
#         data['form']['used_context'] = used_context
#         comparison_context = self._build_comparison_context(data)
#         data['form']['comparison_context'] = comparison_context
#
#         return self.env.ref('accounting_pdf_reports.action_report_financial').with_context(
#             **used_context
#         ).report_action(self, data=data, config=False)
#
#     # -----------------------------
#     # New Button Action (Fix for XML)
#     # -----------------------------
#     # -----------------------------
#     # New Button Action (Fix for XML)
#     # -----------------------------
#     def action_view_details(self):
#         """Open detailed Balance Sheet or P&L in a window with section headers."""
#         self.ensure_one()
#
#         report_type = 'balance_sheet'
#         if self.account_report_id and 'loss' in self.account_report_id.name.lower():
#             report_type = 'profit_loss'
#
#         # Clean old data
#         self.env['account.financial.report.line'].search([]).unlink()
#
#         ctx = self._build_contexts({'form': self.read()[0]})
#         analytic_ids = ctx.get('analytic_account_ids', [])
#         date_from = ctx.get('date_from')
#         date_to = ctx.get('date_to')
#         target_move = ctx.get('target_move', 'posted')
#
#         # Define account type groups
#         if report_type == 'balance_sheet':
#             group_mapping = {
#                 'ASSETS': ['asset_non_current', 'asset_current'],
#                 'LIABILITIES': ['liability_non_current', 'liability_current'],
#                 'EQUITY': ['equity'],
#             }
#         else:
#             group_mapping = {
#                 'INCOME': ['income', 'other_income'],
#                 'EXPENSES': ['expense', 'other_expense'],
#             }
#
#         # ✅ Map internal account types
#         account_type_map = {
#             'ASSETS': 'asset',
#             'LIABILITIES': 'liability',
#             'EQUITY': 'equity',
#             'INCOME': 'income',
#             'EXPENSES': 'expense',
#         }
#
#         ReportLine = self.env['account.financial.report.line']
#         FinancialReport = self.env['report.accounting_pdf_reports.report_financial']
#
#         sequence = 1
#
#         # ✅ Build section-wise account balances
#         for group_name, account_types in group_mapping.items():
#             accounts = self.env['account.account'].search([('account_type', 'in', account_types)])
#             if not accounts:
#                 continue
#
#             account_balances = FinancialReport.with_context(ctx)._compute_account_balance(accounts)
#
#             # Section header
#             ReportLine.create({
#                 'name': f"<b>{group_name}</b>",
#                 'is_section': True,
#                 'sequence': sequence,
#                 'report_type': report_type,
#                 'date_from': date_from,
#                 'date_to': date_to,
#                 'target_move': target_move,
#                 'analytic_account_ids': [(6, 0, analytic_ids)],
#             })
#             sequence += 1
#
#             # Account lines
#             for acc in accounts:
#                 vals = account_balances.get(acc.id)
#                 if not vals:
#                     continue
#                 balance = vals.get('balance', 0)
#                 if abs(balance) < 0.01:
#                     continue
#
#                 ReportLine.create({
#                     'name': acc.name,
#                     'code': acc.code,
#                     'account_id': acc.id,
#                     'debit': vals.get('debit', 0.0),
#                     'credit': vals.get('credit', 0.0),
#                     'balance': balance,
#                     'report_type': report_type,
#                     'sequence': sequence,
#                     'account_type': account_type_map.get(group_name, 'other'),
#                     'date_from': date_from,
#                     'date_to': date_to,
#                     'target_move': target_move,
#                     'analytic_account_ids': [(6, 0, analytic_ids)],
#                 })
#                 sequence += 1
#
#         # ✅ Compute Net Profit / Loss
#         if report_type == 'profit_loss':
#             # -- Calculate total from P&L itself --
#             all_lines = self.env['account.financial.report.line'].search([('report_type', '=', 'profit_loss')])
#             total_debit = sum(all_lines.mapped('debit'))
#             total_credit = sum(all_lines.mapped('credit'))
#             total_balance = sum(all_lines.mapped('balance'))
#
#             total_label = "<b>Net Profit</b>" if total_balance < 0 else "<b>Net Loss</b>"
#
#             ReportLine.create({
#                 'name': total_label,
#                 'is_total': True,
#                 'is_section': False,
#                 'report_type': 'profit_loss',
#                 'debit': total_debit,
#                 'credit': total_credit,
#                 'balance': total_balance,
#                 'sequence': 9999,
#                 'date_from': date_from,
#                 'date_to': date_to,
#                 'target_move': target_move,
#                 'analytic_account_ids': [(6, 0, analytic_ids)],
#             })
#
#         elif report_type == 'balance_sheet':
#             # -- Pull profit/loss from Profit & Loss report for same period --
#             profit_loss_report = self.env['accounting.report'].create({
#                 'date_from': date_from,
#                 'date_to': date_to,
#                 'target_move': target_move,
#             })
#             ctx_pl = profit_loss_report._build_contexts({'form': profit_loss_report.read()[0]})
#             FinancialReportPL = self.env['report.accounting_pdf_reports.report_financial']
#
#             income_accounts = self.env['account.account'].search([('account_type', 'in', ['income', 'other_income'])])
#             expense_accounts = self.env['account.account'].search(
#                 [('account_type', 'in', ['expense', 'other_expense'])])
#
#             income_balance = sum(v['balance'] for v in FinancialReportPL.with_context(ctx_pl)._compute_account_balance(
#                 income_accounts).values())
#             expense_balance = sum(v['balance'] for v in FinancialReportPL.with_context(ctx_pl)._compute_account_balance(
#                 expense_accounts).values())
#             net_profit = income_balance + expense_balance
#             total_label = "<b>Net Profit</b>" if net_profit < 0 else "<b>Net Loss</b>"
#
#             ReportLine.create({
#                 'name': total_label,
#                 'is_total': True,
#                 'is_section': False,
#                 'report_type': 'balance_sheet',
#                 'debit': 0.0,
#                 'credit': 0.0,
#                 'balance': net_profit,
#                 'sequence': 9999,
#                 'date_from': date_from,
#                 'date_to': date_to,
#                 'target_move': target_move,
#                 'analytic_account_ids': [(6, 0, analytic_ids)],
#             })
#
#         # ✅ Return the tree view action
#         return {
#             'type': 'ir.actions.act_window',
#             'name': f'{self.account_report_id.name} Details',
#             'res_model': 'account.financial.report.line',
#             'view_mode': 'list',
#             'target': 'current',
#             'context': ctx,
#             'domain': [('report_type', '=', report_type)],
#         }


# def action_view_details(self):
#     """Open detailed Balance Sheet or P&L in a window with section headers."""
#     self.ensure_one()
#
#     report_type = 'balance_sheet'
#     if self.account_report_id and 'loss' in self.account_report_id.name.lower():
#         report_type = 'profit_loss'
#
#     # Clean old data
#     self.env['account.financial.report.line'].search([]).unlink()
#
#     ctx = self._build_contexts({'form': self.read()[0]})
#     analytic_ids = ctx.get('analytic_account_ids', [])
#     date_from = ctx.get('date_from')
#     date_to = ctx.get('date_to')
#     target_move = ctx.get('target_move', 'posted')
#
#     # Define account type groups
#     if report_type == 'balance_sheet':
#         group_mapping = {
#             'ASSETS': ['asset_non_current', 'asset_current'],
#             'LIABILITIES': ['liability_non_current', 'liability_current'],
#             'EQUITY': ['equity'],
#         }
#     else:
#         group_mapping = {
#             'INCOME': ['income', 'other_income'],
#             'EXPENSES': ['expense', 'other_expense'],
#         }
#
#     # ✅ Define correct Odoo internal account type mapping
#     account_type_map = {
#         'ASSETS': 'asset',
#         'LIABILITIES': 'liability',
#         'EQUITY': 'equity',
#         'INCOME': 'income',
#         'EXPENSES': 'expense',
#     }
#
#     ReportLine = self.env['account.financial.report.line']
#     FinancialReport = self.env['report.accounting_pdf_reports.report_financial']
#
#     sequence = 1
#
#     for group_name, account_types in group_mapping.items():
#         accounts = self.env['account.account'].search([('account_type', 'in', account_types)])
#         if not accounts:
#             continue
#
#         account_balances = FinancialReport.with_context(ctx)._compute_account_balance(accounts)
#
#         # ✅ Create section header
#         section_line = ReportLine.create({
#             'name': group_name,
#             'is_section': True,
#             'sequence': sequence,
#             'report_type': report_type,
#             'date_from': date_from,
#             'date_to': date_to,
#             'target_move': target_move,
#             'analytic_account_ids': [(6, 0, analytic_ids)],
#         })
#         sequence += 1
#
#         # ✅ Add accounts under this section
#         for acc in accounts:
#             vals = account_balances.get(acc.id)
#             if not vals:
#                 continue
#             balance = vals.get('balance', 0)
#             if abs(balance) < 0.01:
#                 continue
#
#             ReportLine.create({
#                 'name': acc.name,
#                 'code': acc.code,
#                 'account_id': acc.id,
#                 'debit': vals.get('debit', 0.0),
#                 'credit': vals.get('credit', 0.0),
#                 'balance': balance,
#                 'report_type': report_type,
#                 'sequence': sequence,
#                 # ✅ Use correct mapping instead of rstrip()
#                 'account_type': account_type_map.get(group_name, 'other'),
#                 'date_from': date_from,
#                 'date_to': date_to,
#                 'target_move': target_move,
#                 'analytic_account_ids': [(6, 0, analytic_ids)],
#             })
#             sequence += 1
#
#     # ✅ Return the tree view action
#     return {
#         'type': 'ir.actions.act_window',
#         'name': f'{self.account_report_id.name} Details',
#         'res_model': 'account.financial.report.line',
#         'view_mode': 'list',
#         'target': 'current',
#         'context': ctx,
#         'domain': [('report_type', '=', report_type)],
#     }

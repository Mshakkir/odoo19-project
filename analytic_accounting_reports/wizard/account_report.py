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
    # Replace the check_report method in your wizard/account_report.py with this:

    def check_report(self):
        """Override to pass data with analytic filtering"""
        self.ensure_one()

        _logger.info("=" * 80)
        _logger.info("🖨️ CHECK_REPORT - Print button clicked")
        _logger.info("Selected analytics: %s", self.analytic_account_ids.mapped('name'))
        _logger.info("=" * 80)

        # Build data dictionary
        data = {
            'ids': self.env.context.get('active_ids', []),
            'model': self.env.context.get('active_model', 'ir.ui.menu'),
            'form': self.read([
                'date_from', 'date_to', 'journal_ids', 'target_move',
                'company_id', 'analytic_account_ids', 'include_combined',
                'account_report_id', 'enable_filter', 'debit_credit',
                'date_from_cmp', 'date_to_cmp', 'filter_cmp', 'label_filter'
            ])[0]
        }

        # Build contexts
        used_context = self._build_contexts(data)
        data['form']['used_context'] = used_context

        # Log what we're passing
        _logger.info("Analytic IDs being passed: %s", used_context.get('analytic_account_ids'))

        # Get report action from parent but DON'T call it yet
        # We need to modify it to use our custom context
        action = self.env.ref('accounting_pdf_reports.action_report_financial').report_action(self, data=data)

        # Force our context into the action
        if 'context' not in action:
            action['context'] = {}
        action['context'].update(used_context)

        _logger.info("=" * 80)
        _logger.info("✅ Returning action with context: %s", action.get('context'))
        _logger.info("=" * 80)

        return action

    # -----------------------------
    # Main Report Action
    # -----------------------------
    def _compute_tax_inclusive_balance(self, accounts, date_from, date_to,
                                       target_move, analytic_ids):
        """
        Compute debit / credit / balance per account using TAX-INCLUSIVE amounts.

        Strategy:
          - For each account.move.line that hits one of the given accounts we
            look at the *parent move* (bill / invoice).
          - We take amount_tax_signed from the move and distribute it to the
            account lines proportionally so that each line's effective amount
            equals its untaxed share + its proportional tax share.
          - Analytic filter is applied by inspecting analytic_distribution JSON
            on the matching move lines.

        Returns dict  { account_id: {'debit': x, 'credit': y, 'balance': z} }
        """
        res = {acc.id: {'debit': 0.0, 'credit': 0.0, 'balance': 0.0}
               for acc in accounts}

        if not accounts:
            return res

        # ------------------------------------------------------------------ #
        # Build base domain for account.move.line                             #
        # ------------------------------------------------------------------ #
        aml_domain = [('account_id', 'in', accounts.ids)]
        if date_from:
            aml_domain.append(('date', '>=', date_from))
        if date_to:
            aml_domain.append(('date', '<=', date_to))
        if target_move == 'posted':
            aml_domain.append(('move_id.state', '=', 'posted'))

        MoveLine = self.env['account.move.line']
        all_lines = MoveLine.search(aml_domain)

        # ------------------------------------------------------------------ #
        # Analytic filter                                                      #
        # ------------------------------------------------------------------ #
        if analytic_ids:
            filtered = []
            for line in all_lines:
                if line.analytic_distribution:
                    for aid in analytic_ids:
                        if str(aid) in line.analytic_distribution:
                            filtered.append(line)
                            break
            matched_lines = MoveLine.browse([l.id for l in filtered])
        else:
            matched_lines = all_lines

        if not matched_lines:
            return res

        # ------------------------------------------------------------------ #
        # Group lines by move so we can add proportional tax                  #
        # ------------------------------------------------------------------ #
        # move_id -> list of aml records (for our accounts only)
        move_to_lines = {}
        for line in matched_lines:
            move_to_lines.setdefault(line.move_id.id, []).append(line)

        move_ids = list(move_to_lines.keys())
        moves = self.env['account.move'].browse(move_ids)
        move_map = {m.id: m for m in moves}

        for move_id, lines in move_to_lines.items():
            move = move_map[move_id]
            tax_amount = abs(move.amount_tax)   # always positive

            # Sum of untaxed absolute amounts across matched lines in this move
            untaxed_total = sum(
                abs(l.debit - l.credit) for l in lines
            )

            for line in lines:
                acc_id = line.account_id.id
                untaxed_line = abs(line.debit - l.credit) if False else abs(line.debit - line.credit)

                # Proportional tax for this line
                if untaxed_total > 0:
                    prop_tax = tax_amount * (untaxed_line / untaxed_total)
                else:
                    prop_tax = 0.0

                tax_incl_amount = untaxed_line + prop_tax

                # Decide debit vs credit based on original sign
                if line.debit >= line.credit:
                    res[acc_id]['debit'] += tax_incl_amount
                else:
                    res[acc_id]['credit'] += tax_incl_amount

                res[acc_id]['balance'] += tax_incl_amount

        return res

    def action_view_details(self):
        """
        Build view details for Balance Sheet or Profit & Loss.
        - Uses TAX-INCLUSIVE amounts (untaxed + proportional tax share)
        - Shows only non-zero accounts
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
        _logger.info("📊 ACTION_VIEW_DETAILS (Tax-Inclusive mode) called")
        _logger.info("Report type: %s", report_type)
        _logger.info("Analytic IDs: %s", analytic_ids)
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

        sequence = 1
        group_totals = {}
        equity_last_account_seq = None

        # Build sections and account lines
        for group_name, account_types in group_mapping.items():
            accounts = self.env['account.account'].search(
                [('account_type', 'in', account_types)]
            )
            if not accounts:
                continue

            # ✅ Use tax-inclusive balances
            balances = self._compute_tax_inclusive_balance(
                accounts, date_from, date_to, target_move, analytic_ids
            )
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

                debit   = vals.get('debit', 0.0)
                credit  = vals.get('credit', 0.0)
                balance = vals.get('balance', 0.0)

                if abs(balance) < 0.0001 and abs(debit) < 0.0001 and abs(credit) < 0.0001:
                    continue

                total_balance += balance
                total_debit   += debit
                total_credit  += credit

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

        # ------------------------------------------------------------------ #
        # Net Profit / Net Loss (tax-inclusive)                               #
        # ------------------------------------------------------------------ #
        if report_type == 'profit_loss':
            income_total  = group_totals.get('INCOME', 0.0)
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
            inc_bal = sum(
                v.get('balance', 0.0) for v in
                self._compute_tax_inclusive_balance(
                    income_accounts, date_from, date_to, target_move, analytic_ids
                ).values()
            )
            exp_bal = sum(
                v.get('balance', 0.0) for v in
                self._compute_tax_inclusive_balance(
                    expense_accounts, date_from, date_to, target_move, analytic_ids
                ).values()
            )
            net = abs(inc_bal) - abs(exp_bal)

        label         = "<b>Net Profit</b>" if net > 0 else "<b>Net Loss</b>"
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
# from collections import OrderedDict
# import logging
#
# _logger = logging.getLogger(__name__)
#
#
# class AccountingReport(models.TransientModel):
#     _inherit = "accounting.report"
#
#     # -----------------------------
#     # Analytic filter fields
#     # -----------------------------
#     analytic_account_ids = fields.Many2many(
#         'account.analytic.account',
#         string="Warehouses",
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
#     @api.onchange('analytic_account_ids')
#     def _onchange_analytic_account_ids(self):
#         if len(self.analytic_account_ids) <= 1:
#             self.include_combined = False
#
#     # -----------------------------
#     # Context Builders - FIXED
#     # -----------------------------
#     def _build_contexts(self, data):
#         """Override to include analytic account IDs in context"""
#
#         analytic_ids = []
#         form_data = data.get('form', {})
#
#         _logger.info("=" * 80)
#         _logger.info("🔧 _build_contexts called")
#         _logger.info("Form data keys: %s", form_data.keys())
#
#         # CRITICAL FIX: Ensure company_id is present before calling parent
#         if 'company_id' not in form_data:
#             company = self.company_id if self.company_id else self.env.company
#             form_data['company_id'] = [company.id, company.name]
#             _logger.info("Added missing company_id: %s", form_data['company_id'])
#
#         # Now safe to call parent
#         result = super()._build_contexts(data)
#
#         # Extract analytic data
#         analytic_data = form_data.get('analytic_account_ids', [])
#         _logger.info("Analytic data raw: %s", analytic_data)
#
#         if analytic_data:
#             if isinstance(analytic_data, (list, tuple)) and len(analytic_data) > 0:
#                 if isinstance(analytic_data[0], (list, tuple)) and len(analytic_data[0]) > 2:
#                     # Format: [(6, 0, [ids])]
#                     analytic_ids = analytic_data[0][2]
#                 else:
#                     # Format: [id1, id2, ...]
#                     analytic_ids = list(analytic_data)
#
#         _logger.info("Extracted analytic_ids: %s", analytic_ids)
#
#         # CRITICAL: Add to context
#         result['analytic_account_ids'] = analytic_ids
#         result['include_combined'] = form_data.get('include_combined', False)
#
#         _logger.info("Final context: %s", result)
#         _logger.info("=" * 80)
#
#         return result
#
#     def _build_comparison_context(self, data):
#         """Override to include analytic account IDs in comparison context"""
#
#         form_data = data.get('form', {})
#
#         # CRITICAL FIX: Ensure company_id is present before calling parent
#         if 'company_id' not in form_data:
#             company = self.company_id if self.company_id else self.env.company
#             form_data['company_id'] = [company.id, company.name]
#
#         result = super()._build_comparison_context(data)
#
#         analytic_ids = []
#         analytic_data = form_data.get('analytic_account_ids', [])
#
#         if analytic_data:
#             if isinstance(analytic_data, (list, tuple)) and len(analytic_data) > 0:
#                 if isinstance(analytic_data[0], (list, tuple)) and len(analytic_data[0]) > 2:
#                     analytic_ids = analytic_data[0][2]
#                 else:
#                     analytic_ids = list(analytic_data)
#
#         result['analytic_account_ids'] = analytic_ids
#         result['include_combined'] = form_data.get('include_combined', False)
#
#         return result
#
#     # -----------------------------
#     # Override check_report to ensure context is passed
#     # -----------------------------
#     # Replace the check_report method in your wizard/account_report.py with this:
#
#     def check_report(self):
#         """Override to pass data with analytic filtering"""
#         self.ensure_one()
#
#         _logger.info("=" * 80)
#         _logger.info("🖨️ CHECK_REPORT - Print button clicked")
#         _logger.info("Selected analytics: %s", self.analytic_account_ids.mapped('name'))
#         _logger.info("=" * 80)
#
#         # Build data dictionary
#         data = {
#             'ids': self.env.context.get('active_ids', []),
#             'model': self.env.context.get('active_model', 'ir.ui.menu'),
#             'form': self.read([
#                 'date_from', 'date_to', 'journal_ids', 'target_move',
#                 'company_id', 'analytic_account_ids', 'include_combined',
#                 'account_report_id', 'enable_filter', 'debit_credit',
#                 'date_from_cmp', 'date_to_cmp', 'filter_cmp', 'label_filter'
#             ])[0]
#         }
#
#         # Build contexts
#         used_context = self._build_contexts(data)
#         data['form']['used_context'] = used_context
#
#         # Log what we're passing
#         _logger.info("Analytic IDs being passed: %s", used_context.get('analytic_account_ids'))
#
#         # Get report action from parent but DON'T call it yet
#         # We need to modify it to use our custom context
#         action = self.env.ref('accounting_pdf_reports.action_report_financial').report_action(self, data=data)
#
#         # Force our context into the action
#         if 'context' not in action:
#             action['context'] = {}
#         action['context'].update(used_context)
#
#         _logger.info("=" * 80)
#         _logger.info("✅ Returning action with context: %s", action.get('context'))
#         _logger.info("=" * 80)
#
#         return action
#
#     # -----------------------------
#     # Main Report Action
#     # -----------------------------
#     def action_view_details(self):
#         """
#         Build view details for Balance Sheet or Profit & Loss.
#         - Shows only non-zero accounts
#         - Shows Income & Expense as positive
#         - Places Net Profit/Loss immediately after the last Equity account
#         """
#         self.ensure_one()
#         report_type = 'balance_sheet'
#         if self.account_report_id and 'loss' in self.account_report_id.name.lower():
#             report_type = 'profit_loss'
#
#         # Clear old temporary lines
#         self.env['account.financial.report.line'].search([]).unlink()
#
#         ctx = self._build_contexts({'form': self.read()[0]})
#         analytic_ids = ctx.get('analytic_account_ids', [])
#         date_from = ctx.get('date_from')
#         date_to = ctx.get('date_to')
#         target_move = ctx.get('target_move', 'posted')
#
#         _logger.info("=" * 80)
#         _logger.info("📊 ACTION_VIEW_DETAILS (Show Details) called")
#         _logger.info("Report type: %s", report_type)
#         _logger.info("Context analytic_ids: %s", analytic_ids)
#         _logger.info("Full context: %s", ctx)
#         _logger.info("=" * 80)
#
#         # Account groups (ordered)
#         if report_type == 'balance_sheet':
#             group_mapping = OrderedDict([
#                 ('ASSETS', [
#                     'asset_receivable', 'asset_bank', 'asset_cash',
#                     'asset_current', 'asset_non_current',
#                     'asset_prepayments', 'asset_fixed'
#                 ]),
#                 ('LIABILITIES', [
#                     'liability_payable', 'liability_credit_card',
#                     'liability_current', 'liability_non_current'
#                 ]),
#                 ('EQUITY', [
#                     'equity', 'equity_current_earnings'
#                 ]),
#             ])
#         else:
#             group_mapping = OrderedDict([
#                 ('INCOME', [
#                     'income', 'other_income'
#                 ]),
#                 ('EXPENSES', [
#                     'expense', 'other_expense', 'depreciation',
#                     'expense_direct_cost', 'expense_cost_of_revenue'
#                 ]),
#             ])
#
#         ReportLine = self.env['account.financial.report.line']
#         FinancialReport = self.env['report.accounting_pdf_reports.report_financial']
#
#         sequence = 1
#         group_totals = {}
#         equity_last_account_seq = None
#
#         # Build sections and account lines
#         for group_name, account_types in group_mapping.items():
#             accounts = self.env['account.account'].search([('account_type', 'in', account_types)])
#             if not accounts:
#                 continue
#
#             balances = FinancialReport.with_context(ctx)._compute_account_balance(accounts)
#             total_balance = total_debit = total_credit = 0.0
#
#             # Create section header
#             section = ReportLine.create({
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
#             # Create account lines
#             for acc in accounts:
#                 vals = balances.get(acc.id)
#                 if not vals:
#                     continue
#
#                 balance = abs(vals.get('balance', 0.0))
#                 debit = vals.get('debit', 0.0)
#                 credit = vals.get('credit', 0.0)
#
#                 if abs(balance) < 0.0001 and abs(debit) < 0.0001 and abs(credit) < 0.0001:
#                     continue
#
#                 total_balance += balance
#                 total_debit += debit
#                 total_credit += credit
#
#                 ReportLine.create({
#                     'name': acc.name,
#                     'code': acc.code,
#                     'account_id': acc.id,
#                     'debit': debit,
#                     'credit': credit,
#                     'balance': balance,
#                     'report_type': report_type,
#                     'sequence': sequence,
#                     'date_from': date_from,
#                     'date_to': date_to,
#                     'target_move': target_move,
#                     'analytic_account_ids': [(6, 0, analytic_ids)],
#                 })
#
#                 if group_name == 'EQUITY':
#                     equity_last_account_seq = sequence
#
#                 sequence += 1
#
#             section.write({
#                 'debit': total_debit,
#                 'credit': total_credit,
#                 'balance': total_balance,
#             })
#
#             group_totals[group_name] = total_balance
#             sequence += 1
#
#         # Net Profit / Net Loss
#         if report_type == 'profit_loss':
#             income_total = group_totals.get('INCOME', 0.0)
#             expense_total = group_totals.get('EXPENSES', 0.0)
#             net = income_total - expense_total
#         else:
#             income_accounts = self.env['account.account'].search([
#                 ('account_type', 'in', ['income', 'other_income'])
#             ])
#             expense_accounts = self.env['account.account'].search([
#                 ('account_type', 'in', ['expense', 'other_expense', 'depreciation',
#                                         'expense_direct_cost', 'expense_cost_of_revenue'])
#             ])
#
#             inc_bal = sum(v.get('balance', 0.0) for v in
#                           FinancialReport.with_context(ctx)._compute_account_balance(income_accounts).values())
#             exp_bal = sum(v.get('balance', 0.0) for v in
#                           FinancialReport.with_context(ctx)._compute_account_balance(expense_accounts).values())
#
#             net = abs(inc_bal) - abs(exp_bal)
#
#         label = "<b>Net Profit</b>" if net > 0 else "<b>Net Loss</b>"
#         display_value = abs(net)
#
#         if report_type == 'balance_sheet' and equity_last_account_seq:
#             insert_sequence = equity_last_account_seq + 1
#         else:
#             insert_sequence = sequence + 1
#
#         ReportLine.create({
#             'name': label,
#             'is_total': True,
#             'report_type': report_type,
#             'balance': display_value,
#             'sequence': insert_sequence,
#             'date_from': date_from,
#             'date_to': date_to,
#             'target_move': target_move,
#             'analytic_account_ids': [(6, 0, analytic_ids)],
#         })
#
#         return {
#             'type': 'ir.actions.act_window',
#             'name': f'{self.account_report_id.name} Details',
#             'res_model': 'account.financial.report.line',
#             'view_mode': 'list',
#             'target': 'current',
#             'domain': [('report_type', '=', report_type)],
#             'context': ctx,
#         }
#

# -*- coding: utf-8 -*-
from odoo import models, fields, api


class AccountingReport(models.TransientModel):
    _inherit = 'accounting.report'

    warehouse_analytic_ids = fields.Many2many(
        'account.analytic.account',
        string='Warehouse Analytic Accounts',
        help='Select one or more analytic accounts (linked to warehouses) to filter the Balance Sheet report.'
    )

    # -------------------------------------------------------------------------
    # BALANCE SHEET LOGIC
    # -------------------------------------------------------------------------
    def action_view_balance_sheet_details(self):
        """Generate balance sheet lines."""
        self.ensure_one()
        self.env['custom.balance.sheet.line'].search([]).unlink()

        lines = self._get_balance_sheet_lines()
        for line in lines:
            account_type = line['account_type']
            section_type = self._map_section_type(account_type)

            self.env['custom.balance.sheet.line'].create({
                'name': line['account_name'],
                'account_type': account_type,
                'section_type': section_type,
                'debit': line['debit'] or 0.0,
                'credit': line['credit'] or 0.0,
                'balance': line['balance'] or 0.0,
                'currency_id': self.env.company.currency_id.id,
                'account_id': line.get('account_id'),
            })

        return {
            'name': 'Balance Sheet Details',
            'type': 'ir.actions.act_window',
            'res_model': 'custom.balance.sheet.line',
            'view_mode': 'list',
            'views': [(self.env.ref('custom_bs_pl_module.view_account_list_balance_sheet').id, 'list')],
            'target': 'current',
            'context': {'group_by': ['section_type']},
        }

    def _get_balance_sheet_lines(self):
        date_from = self.date_from or None
        date_to = self.date_to or None
        params = [self.env.company.id]
        date_filter_sql = ""
        analytic_join_sql = ""
        analytic_filter_sql = ""

        # ✅ Date filters
        if date_from:
            date_filter_sql += " AND aml.date >= %s"
            params.append(date_from)
        if date_to:
            date_filter_sql += " AND aml.date <= %s"
            params.append(date_to)

        # ✅ Analytic filter (Community Edition)
        if self.warehouse_analytic_ids:
            analytic_ids = tuple(self.warehouse_analytic_ids.ids)
            analytic_join_sql = """
                JOIN account_analytic_line aal
                  ON aal.move_id = aml.id
            """
            if len(analytic_ids) == 1:
                analytic_filter_sql = f" AND aal.account_id = {analytic_ids[0]}"
            else:
                analytic_filter_sql = f" AND aal.account_id IN {analytic_ids}"

        # ✅ Main Query
        query = f"""
            SELECT
                aa.id as account_id,
                aa.name as account_name,
                aa.account_type as account_type,
                SUM(aml.debit) AS debit,
                SUM(aml.credit) AS credit,
                SUM(aml.debit - aml.credit) AS balance
            FROM account_move_line aml
            JOIN account_move am ON aml.move_id = am.id
            JOIN account_account aa ON aml.account_id = aa.id
            {analytic_join_sql}
            WHERE aml.company_id = %s
              AND am.state = 'posted'
              {date_filter_sql}
              {analytic_filter_sql}
            GROUP BY aa.id, aa.name, aa.account_type
            HAVING COALESCE(SUM(aml.debit),0) != 0 OR COALESCE(SUM(aml.credit),0) != 0
            ORDER BY aa.account_type, aa.name
        """

        self.env.cr.execute(query, params)
        return self.env.cr.dictfetchall()

    def _map_section_type(self, account_type):
        """Map account_type → section group"""
        if account_type.startswith('asset'):
            return 'asset'
        elif account_type.startswith('liability'):
            return 'liability'
        elif account_type.startswith('equity'):
            return 'equity'
        else:
            return 'profit_loss'

    # -------------------------------------------------------------------------
    # PROFIT & LOSS LOGIC
    # -------------------------------------------------------------------------
    def action_view_profit_loss_details(self):
        """Open Profit & Loss details view"""
        self.ensure_one()
        pl_types = [
            'income',
            'income_other',
            'expense',
            'expense_depreciation',
            'expense_direct_cost',
        ]
        accounts = self.env['account.account'].search([('account_type', 'in', pl_types)])
        return {
            'name': 'Profit & Loss Details',
            'type': 'ir.actions.act_window',
            'res_model': 'account.account',
            'view_mode': 'list',
            'views': [(self.env.ref('custom_bs_pl_module.view_account_list_profit_loss').id, 'list')],
            'domain': [('id', 'in', accounts.ids)],
            'context': {
                'date_from': self.date_from,
                'date_to': self.date_to,
                'company_id': self.company_id.id,
            },
            'target': 'current',
        }

# # -*- coding: utf-8 -*-
# from odoo import models, fields, api
#
#
# class AccountingReport(models.TransientModel):
#     _inherit = 'accounting.report'
#
#     # -------------------------------------------------------------------------
#     # WAREHOUSE ANALYTIC FILTER
#     # -------------------------------------------------------------------------
#     warehouse_analytic_ids = fields.Many2many(
#         'account.analytic.account',
#         string='Warehouse Analytics',
#         help='Select one or more warehouse analytic accounts to filter the report.'
#     )
#
#     # -------------------------------------------------------------------------
#     # BALANCE SHEET LOGIC
#     # -------------------------------------------------------------------------
#     def action_view_balance_sheet_details(self):
#         """Generate balance sheet lines with warehouse filtering."""
#         self.ensure_one()
#         self.env['custom.balance.sheet.line'].search([]).unlink()
#
#         lines = self._get_balance_sheet_lines()
#         for line in lines:
#             self.env['custom.balance.sheet.line'].create({
#                 'name': line['account_name'],
#                 'account_type': line['account_type'],
#                 'section_type': line['section_type'],
#                 'debit': line['debit'] or 0.0,
#                 'credit': line['credit'] or 0.0,
#                 'balance': line['balance'] or 0.0,
#                 'currency_id': self.env.company.currency_id.id,
#                 'account_id': line.get('account_id'),
#             })
#
#         # Build context with filter info
#         context = {
#             'group_by': ['section_type'],
#             'date_from': self.date_from,
#             'date_to': self.date_to,
#             'company_id': self.company_id.id,
#         }
#
#         # Add warehouse info to window name
#         window_name = 'Balance Sheet Details'
#         if self.warehouse_analytic_ids:
#             warehouse_names = ', '.join(self.warehouse_analytic_ids.mapped('name'))
#             window_name = f'Balance Sheet Details - {warehouse_names}'
#
#         return {
#             'name': window_name,
#             'type': 'ir.actions.act_window',
#             'res_model': 'custom.balance.sheet.line',
#             'view_mode': 'list',
#             'views': [(self.env.ref('custom_bs_pl_module.view_account_list_balance_sheet').id, 'list')],
#             'target': 'current',
#             'context': context,
#         }
#
#     def _get_balance_sheet_lines(self):
#         """
#         Compute balance sheet lines filtered by warehouse analytics.
#         Returns lines for Assets, Liabilities, and Equity.
#         """
#         date_from = self.date_from or None
#         date_to = self.date_to or None
#         params = [self.env.company.id]
#         date_filter_sql = ""
#
#         # Date filter
#         if date_from:
#             date_filter_sql += " AND aml.date >= %s"
#             params.append(date_from)
#         if date_to:
#             date_filter_sql += " AND aml.date <= %s"
#             params.append(date_to)
#
#         # Warehouse analytic filter
#         analytic_filter_sql = ""
#         if self.warehouse_analytic_ids:
#             analytic_filter_sql = " AND aml.analytic_account_id IN %s"
#             params.append(tuple(self.warehouse_analytic_ids.ids))
#
#         # Main query (removed aa.code - not available in Odoo 19)
#         query = f"""
#             SELECT
#                 aa.id as account_id,
#                 aa.name as account_name,
#                 aa.account_type as account_type,
#                 SUM(aml.debit) AS debit,
#                 SUM(aml.credit) AS credit,
#                 SUM(aml.debit - aml.credit) AS balance
#             FROM account_move_line aml
#             JOIN account_move am ON aml.move_id = am.id
#             JOIN account_account aa ON aml.account_id = aa.id
#             WHERE aml.company_id = %s
#               AND am.state = 'posted'
#               {date_filter_sql}
#               {analytic_filter_sql}
#             GROUP BY aa.id, aa.name, aa.account_type
#             HAVING COALESCE(SUM(aml.debit),0) != 0 OR COALESCE(SUM(aml.credit),0) != 0
#             ORDER BY aa.account_type, aa.name
#         """
#
#         self.env.cr.execute(query, params)
#         result = self.env.cr.dictfetchall()
#
#         asset_lines, liability_lines, equity_lines = [], [], []
#
#         # Categorize accounts by type
#         for line in result:
#             acc_type = line['account_type']
#
#             if acc_type.startswith('asset'):
#                 line['section_type'] = 'asset'
#                 asset_lines.append(line)
#             elif acc_type.startswith('liability'):
#                 line['section_type'] = 'liability'
#                 liability_lines.append(line)
#             elif acc_type.startswith('equity'):
#                 line['section_type'] = 'equity'
#                 equity_lines.append(line)
#
#         return asset_lines + liability_lines + equity_lines
#
#     # -------------------------------------------------------------------------
#     # PROFIT & LOSS LOGIC
#     # -------------------------------------------------------------------------
#     def action_view_profit_loss_details(self):
#         """Open Profit & Loss details view with warehouse filtering"""
#         self.ensure_one()
#
#         pl_types = [
#             'income',
#             'income_other',
#             'expense',
#             'expense_depreciation',
#             'expense_direct_cost',
#         ]
#
#         accounts = self.env['account.account'].search([('account_type', 'in', pl_types)])
#
#         # Build window name with warehouse info
#         window_name = 'Profit & Loss Details'
#         if self.warehouse_analytic_ids:
#             warehouse_names = ', '.join(self.warehouse_analytic_ids.mapped('name'))
#             window_name = f'Profit & Loss Details - {warehouse_names}'
#
#         # Pass warehouse filter to context
#         context = {
#             'date_from': self.date_from,
#             'date_to': self.date_to,
#             'company_id': self.company_id.id,
#             'warehouse_analytic_ids': self.warehouse_analytic_ids.ids,
#         }
#
#         return {
#             'name': window_name,
#             'type': 'ir.actions.act_window',
#             'res_model': 'account.account',
#             'view_mode': 'list',
#             'views': [(self.env.ref('custom_bs_pl_module.view_account_list_profit_loss').id, 'list')],
#             'domain': [('id', 'in', accounts.ids)],
#             'context': context,
#             'target': 'current',
#         }

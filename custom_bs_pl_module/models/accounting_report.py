# -*- coding: utf-8 -*-
from odoo import models, fields, api


class AccountingReport(models.TransientModel):
    _inherit = 'accounting.report'

    # New Fields
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        help='Select warehouse to view balance sheet for a specific location',
    )
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        help='Filter report by analytic account (overrides warehouse if set)',
    )
    include_all = fields.Boolean(
        string='Include All Warehouses',
        default=False,
        help='If checked, combine all warehouses',
    )

    # -------------------------------------------------------------------------
    # BALANCE SHEET LOGIC
    # -------------------------------------------------------------------------
    def action_view_balance_sheet_details(self):
        """Generate balance sheet lines filtered by warehouse or analytic (if selected)."""
        self.ensure_one()
        self.env['custom.balance.sheet.line'].search([]).unlink()

        lines = self._get_balance_sheet_lines()
        for line in lines:
            account_type = line['account_type'] or ''
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
            'name': f'Balance Sheet Details - {self._get_filter_label()}',
            'type': 'ir.actions.act_window',
            'res_model': 'custom.balance.sheet.line',
            'view_mode': 'list',
            'views': [(self.env.ref('custom_bs_pl_module.view_account_list_balance_sheet').id, 'list')],
            'target': 'current',
            'context': {'group_by': ['section_type']},
        }

    def _get_balance_sheet_lines(self):
        """
        Return list of dicts: account_id, account_name, account_type, debit, credit, balance.
        Filters: Only posted entries and optionally by warehouse or analytic_account_id.
        """
        date_from = self.date_from or None
        date_to = self.date_to or None
        params = [self.env.company.id]
        date_filter_sql = ""

        if date_from:
            date_filter_sql += " AND aml.date >= %s"
            params.append(date_from)
        if date_to:
            date_filter_sql += " AND aml.date <= %s"
            params.append(date_to)

        # Decide filter priority: analytic_account_id overrides warehouse filter if present
        warehouse_filter_sql = ""
        analytic_filter_sql = ""
        if self.analytic_account_id:
            analytic_filter_sql += " AND aml.analytic_account_id = %s"
            params.append(self.analytic_account_id.id)
        else:
            if not self.include_all and self.warehouse_id:
                warehouse_filter_sql += " AND am.warehouse_id = %s"
                params.append(self.warehouse_id.id)

        query = f"""
            SELECT
                aa.id as account_id,
                aa.name as account_name,
                aa.account_type as account_type,
                COALESCE(SUM(aml.debit),0) AS debit,
                COALESCE(SUM(aml.credit),0) AS credit,
                COALESCE(SUM(aml.debit - aml.credit),0) AS balance
            FROM account_move_line aml
            JOIN account_move am ON aml.move_id = am.id
            JOIN account_account aa ON aml.account_id = aa.id
            WHERE aml.company_id = %s
              AND am.state = 'posted'
              {date_filter_sql}
              {warehouse_filter_sql}
              {analytic_filter_sql}
            GROUP BY aa.id, aa.name, aa.account_type
            HAVING COALESCE(SUM(aml.debit),0) != 0 OR COALESCE(SUM(aml.credit),0) != 0
            ORDER BY aa.account_type, aa.name
        """
        self.env.cr.execute(query, params)
        return self.env.cr.dictfetchall()

    def _map_section_type(self, account_type):
        """Map account_type → section group"""
        if not account_type:
            return 'profit_loss'
        if account_type.startswith('asset'):
            return 'asset'
        elif account_type.startswith('liability'):
            return 'liability'
        elif account_type.startswith('equity'):
            return 'equity'
        else:
            return 'profit_loss'

    def _get_filter_label(self):
        """Readable description for the current filter selection"""
        if self.analytic_account_id:
            return self.analytic_account_id.name
        if self.include_all:
            return "All Warehouses"
        elif self.warehouse_id:
            return self.warehouse_id.name
        return "No Warehouse / No Analytic"

    # -------------------------------------------------------------------------
    # PROFIT & LOSS LOGIC
    # -------------------------------------------------------------------------
    def action_view_profit_loss_details(self):
        """Open Profit & Loss details view for accounts that have activity under selected filters."""
        self.ensure_one()
        pl_types = [
            'income',
            'income_other',
            'expense',
            'expense_depreciation',
            'expense_direct_cost',
        ]

        # Build SQL to get accounts with activity filtered by analytic/warehouse + date/company
        date_from = self.date_from or None
        date_to = self.date_to or None
        params = [self.env.company.id]
        date_filter_sql = ""
        if date_from:
            date_filter_sql += " AND aml.date >= %s"
            params.append(date_from)
        if date_to:
            date_filter_sql += " AND aml.date <= %s"
            params.append(date_to)

        # filters
        warehouse_filter_sql = ""
        analytic_filter_sql = ""
        if self.analytic_account_id:
            analytic_filter_sql += " AND aml.analytic_account_id = %s"
            params.append(self.analytic_account_id.id)
        else:
            if not self.include_all and self.warehouse_id:
                warehouse_filter_sql += " AND am.warehouse_id = %s"
                params.append(self.warehouse_id.id)

        query = f"""
            SELECT DISTINCT aa.id
            FROM account_move_line aml
            JOIN account_move am ON aml.move_id = am.id
            JOIN account_account aa ON aml.account_id = aa.id
            WHERE aml.company_id = %s
              AND am.state = 'posted'
              AND aa.account_type IN %s
              {date_filter_sql}
              {warehouse_filter_sql}
              {analytic_filter_sql}
        """
        # account types tuple param must be passed separately
        params_for_query = params + [tuple(pl_types)]
        # execute with account types tuple as last parameter
        self.env.cr.execute(query, params_for_query)
        rows = self.env.cr.fetchall()
        account_ids = [r[0] for r in rows] if rows else []

        return {
            'name': f'Profit & Loss Details - {self._get_filter_label()}',
            'type': 'ir.actions.act_window',
            'res_model': 'account.account',
            'view_mode': 'list,form',
            'views': [(self.env.ref('custom_bs_pl_module.view_account_list_profit_loss').id, 'list')],
            'domain': [('id', 'in', account_ids)],
            'context': {
                'date_from': self.date_from,
                'date_to': self.date_to,
                'company_id': self.company_id.id,
                'analytic_account_id': self.analytic_account_id.id if self.analytic_account_id else False,
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
#     # New Fields
#     warehouse_id = fields.Many2one(
#         'stock.warehouse',
#         string='Warehouse',
#         help='Select warehouse to view balance sheet for a specific location',
#     )
#     include_all = fields.Boolean(
#         string='Include All Warehouses',
#         default=False,
#         help='If checked, combine all warehouses',
#     )
#
#     # -------------------------------------------------------------------------
#     # BALANCE SHEET LOGIC
#     # -------------------------------------------------------------------------
#     def action_view_balance_sheet_details(self):
#         """Generate balance sheet lines filtered by warehouse (if selected)."""
#         self.ensure_one()
#         self.env['custom.balance.sheet.line'].search([]).unlink()
#
#         lines = self._get_balance_sheet_lines()
#         for line in lines:
#             account_type = line['account_type']
#             section_type = self._map_section_type(account_type)
#
#             self.env['custom.balance.sheet.line'].create({
#                 'name': line['account_name'],
#                 'account_type': account_type,
#                 'section_type': section_type,
#                 'debit': line['debit'] or 0.0,
#                 'credit': line['credit'] or 0.0,
#                 'balance': line['balance'] or 0.0,
#                 'currency_id': self.env.company.currency_id.id,
#                 'account_id': line.get('account_id'),
#             })
#
#         return {
#             'name': f'Balance Sheet Details - {self._get_warehouse_label()}',
#             'type': 'ir.actions.act_window',
#             'res_model': 'custom.balance.sheet.line',
#             'view_mode': 'list',
#             'views': [(self.env.ref('custom_bs_pl_module.view_account_list_balance_sheet').id, 'list')],
#             'target': 'current',
#             'context': {'group_by': ['section_type']},
#         }
#
#     def _get_balance_sheet_lines(self):
#         """
#         Return list of dicts: account_id, account_name, account_type, debit, credit, balance.
#         Filters: Only posted entries and optionally by warehouse.
#         """
#         date_from = self.date_from or None
#         date_to = self.date_to or None
#         params = [self.env.company.id]
#         date_filter_sql = ""
#
#         if date_from:
#             date_filter_sql += " AND aml.date >= %s"
#             params.append(date_from)
#         if date_to:
#             date_filter_sql += " AND aml.date <= %s"
#             params.append(date_to)
#
#         # Warehouse filter
#         warehouse_filter_sql = ""
#         if not self.include_all and self.warehouse_id:
#             warehouse_filter_sql += " AND am.warehouse_id = %s"
#             params.append(self.warehouse_id.id)
#
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
#               {warehouse_filter_sql}
#             GROUP BY aa.id, aa.name, aa.account_type
#             HAVING COALESCE(SUM(aml.debit),0) != 0 OR COALESCE(SUM(aml.credit),0) != 0
#             ORDER BY aa.account_type, aa.name
#         """
#         self.env.cr.execute(query, params)
#         return self.env.cr.dictfetchall()
#
#     def _map_section_type(self, account_type):
#         """Map account_type → section group"""
#         if account_type.startswith('asset'):
#             return 'asset'
#         elif account_type.startswith('liability'):
#             return 'liability'
#         elif account_type.startswith('equity'):
#             return 'equity'
#         else:
#             return 'profit_loss'
#
#     def _get_warehouse_label(self):
#         """Readable name for warehouse"""
#         if self.include_all:
#             return "All Warehouses"
#         elif self.warehouse_id:
#             return self.warehouse_id.name
#         return "No Warehouse"
#
#     # -------------------------------------------------------------------------
#     # PROFIT & LOSS LOGIC
#     # -------------------------------------------------------------------------
#     def action_view_profit_loss_details(self):
#         """Open Profit & Loss details view"""
#         self.ensure_one()
#         pl_types = [
#             'income',
#             'income_other',
#             'expense',
#             'expense_depreciation',
#             'expense_direct_cost',
#         ]
#         accounts = self.env['account.account'].search([('account_type', 'in', pl_types)])
#         return {
#             'name': 'Profit & Loss Details',
#             'type': 'ir.actions.act_window',
#             'res_model': 'account.account',
#             'view_mode': 'list',
#             'views': [(self.env.ref('custom_bs_pl_module.view_account_list_profit_loss').id, 'list')],
#             'domain': [('id', 'in', accounts.ids)],
#             'context': {
#                 'date_from': self.date_from,
#                 'date_to': self.date_to,
#                 'company_id': self.company_id.id,
#             },
#             'target': 'current',
#         }
#
#
#

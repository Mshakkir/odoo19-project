# from odoo import api, models
#
#
# class ReportFinancial(models.AbstractModel):
#     _inherit = 'report.accounting_pdf_reports.report_financial'
#
#     def _compute_account_balance(self, accounts):
#         """Override to add analytic distribution filtering"""
#         mapping = {
#             'balance': "COALESCE(SUM(debit),0) - COALESCE(SUM(credit), 0) as balance",
#             'debit': "COALESCE(SUM(debit), 0) as debit",
#             'credit': "COALESCE(SUM(credit), 0) as credit",
#         }
#
#         res = {}
#         for account in accounts:
#             # initialize each account row with 0.0 for the keys we want
#             res[account.id] = {k: 0.0 for k in mapping.keys()}
#
#         if not accounts:
#             return res
#
#         # build base query parts using Odoo helper
#         tables, where_clause, where_params = self.env['account.move.line']._query_get()
#         # fallback defaults
#         tables = (tables or "account_move_line").replace('"', '')
#         where_clause = where_clause.strip() if where_clause else ''
#         where_params = where_params or []
#
#         # assemble where parts cleanly
#         wheres = []
#         if where_clause:
#             wheres.append("(%s)" % where_clause)
#
#         analytic_account_ids = self.env.context.get('analytic_account_ids', []) or []
#         if analytic_account_ids:
#             analytic_conditions = []
#             for analytic_id in analytic_account_ids:
#                 # match either the key existence or key with a nested object/value
#                 analytic_conditions.append(
#                     f"(analytic_distribution::text LIKE '%\"{int(analytic_id)}\"%' OR analytic_distribution::text LIKE '%\"{int(analytic_id)}\":%')"
#                 )
#             if analytic_conditions:
#                 wheres.append("(" + " OR ".join(analytic_conditions) + ")")
#
#         filters = (" AND ".join(wheres)) and " AND " + " AND ".join(wheres) or ""
#
#         request = (
#             "SELECT account_id as id, " + ', '.join(mapping.values()) +
#             " FROM " + tables +
#             " WHERE account_id IN %s " + filters +
#             " GROUP BY account_id"
#         )
#
#         params = [tuple(accounts.ids)] + list(where_params)
#         self.env.cr.execute(request, tuple(params))
#         for row in self.env.cr.dictfetchall():
#             res[row['id']] = {
#                 'balance': row.get('balance', 0.0),
#                 'debit': row.get('debit', 0.0),
#                 'credit': row.get('credit', 0.0),
#             }
#
#         return res
#
#     def _get_warehouse_breakdown(self, accounts):
#         """Get balance breakdown by warehouse for the accounts"""
#         if not accounts:
#             return {}, []
#
#         analytic_account_ids = self.env.context.get('analytic_account_ids', []) or []
#
#         if analytic_account_ids:
#             warehouses = self.env['account.analytic.account'].browse(analytic_account_ids)
#         else:
#             warehouses = self.env['account.analytic.account'].search([
#                 ('name', 'ilike', 'SSAQCO')
#             ], order='name')
#
#         if not warehouses:
#             return {}, []
#
#         # prepare result structure
#         result = {account.id: {w.id: {'balance': 0.0, 'debit': 0.0, 'credit': 0.0, 'name': w.name}
#                                for w in warehouses} for account in accounts}
#
#         tables, where_clause, where_params = self.env['account.move.line']._query_get()
#         tables = (tables or "account_move_line").replace('"', '')
#         where_clause = where_clause.strip() if where_clause else ''
#         where_params = where_params or []
#
#         for warehouse in warehouses:
#             wheres = []
#             if where_clause:
#                 wheres.append("(%s)" % where_clause)
#
#             wheres.append(
#                 f"(analytic_distribution::text LIKE '%\"{int(warehouse.id)}\"%' OR analytic_distribution::text LIKE '%\"{int(warehouse.id)}\":%')"
#             )
#
#             filters = (" AND ".join(wheres)) and " AND " + " AND ".join(wheres) or ""
#
#             request = f"""
#                 SELECT account_id,
#                        COALESCE(SUM(debit), 0) as debit,
#                        COALESCE(SUM(credit), 0) as credit,
#                        COALESCE(SUM(debit), 0) - COALESCE(SUM(credit), 0) as balance
#                 FROM {tables}
#                 WHERE account_id IN %s {filters}
#                 GROUP BY account_id
#             """
#             params = [tuple(accounts.ids)] + list(where_params)
#             self.env.cr.execute(request, tuple(params))
#             for row in self.env.cr.dictfetchall():
#                 acc_id = row.get('account_id')
#                 if acc_id in result:
#                     result[acc_id][warehouse.id] = {
#                         'balance': row.get('balance', 0.0),
#                         'debit': row.get('debit', 0.0),
#                         'credit': row.get('credit', 0.0),
#                         'name': warehouse.name
#                     }
#
#         return result, warehouses
#
#     @api.model
#     def _get_report_values(self, docids, data=None):
#         """Override to pass analytic information for display"""
#         result = super(ReportFinancial, self)._get_report_values(docids, data) or {}
#
#         # default values
#         result['selected_warehouses'] = False
#         result['warehouse_display'] = 'All Warehouses'
#         result['include_combined'] = False
#
#         if data and data.get('form'):
#             analytic_data = data['form'].get('analytic_account_ids', [])
#             analytic_ids = []
#             # normalize
#             if analytic_data and isinstance(analytic_data[0], (list, tuple)):
#                 analytic_ids = analytic_data[0][2] if len(analytic_data[0]) > 2 else []
#             else:
#                 analytic_ids = analytic_data or []
#
#             if analytic_ids:
#                 analytic_accounts = self.env['account.analytic.account'].browse(analytic_ids)
#                 result['selected_warehouses'] = analytic_accounts
#                 names = [acc.name for acc in analytic_accounts]
#                 result['warehouse_display'] = ', '.join(names) if names else 'All Warehouses'
#             else:
#                 result['selected_warehouses'] = False
#                 result['warehouse_display'] = 'All Warehouses'
#
#             result['include_combined'] = bool(data['form'].get('include_combined', False))
#
#         return result

# second code get only combined datas
# from odoo import api, models
#
#
# class ReportFinancial(models.AbstractModel):
#     _inherit = 'report.accounting_pdf_reports.report_financial'
#
#     def _compute_account_balance(self, accounts):
#         """Override to add analytic distribution filtering"""
#         mapping = {
#             'balance': "COALESCE(SUM(debit),0) - COALESCE(SUM(credit), 0) as balance",
#             'debit': "COALESCE(SUM(debit), 0) as debit",
#             'credit': "COALESCE(SUM(credit), 0) as credit",
#         }
#
#         res = {}
#         for account in accounts:
#             res[account.id] = {k: 0.0 for k in mapping.keys()}
#
#         if not accounts:
#             return res
#
#         # Build base query parts
#         tables, where_clause, where_params = self.env['account.move.line']._query_get()
#         tables = (tables or "account_move_line").replace('"', '')
#         where_clause = where_clause.strip() if where_clause else ''
#         where_params = where_params or []
#
#         # Build WHERE conditions
#         wheres = []
#         if where_clause:
#             wheres.append("(%s)" % where_clause)
#
#         # Add analytic filter if present
#         analytic_account_ids = self.env.context.get('analytic_account_ids', [])
#         if analytic_account_ids:
#             analytic_conditions = []
#             for analytic_id in analytic_account_ids:
#                 analytic_conditions.append(
#                     f"(analytic_distribution::text LIKE '%\"{int(analytic_id)}\"%' OR "
#                     f"analytic_distribution::text LIKE '%\"{int(analytic_id)}\":%')"
#                 )
#             if analytic_conditions:
#                 wheres.append("(" + " OR ".join(analytic_conditions) + ")")
#
#         filters = (" AND ".join(wheres)) and " AND " + " AND ".join(wheres) or ""
#
#         request = (
#                 "SELECT account_id as id, " + ', '.join(mapping.values()) +
#                 " FROM " + tables +
#                 " WHERE account_id IN %s " + filters +
#                 " GROUP BY account_id"
#         )
#
#         params = [tuple(accounts.ids)] + list(where_params)
#         self.env.cr.execute(request, tuple(params))
#
#         for row in self.env.cr.dictfetchall():
#             res[row['id']] = {
#                 'balance': row.get('balance', 0.0),
#                 'debit': row.get('debit', 0.0),
#                 'credit': row.get('credit', 0.0),
#             }
#
#         return res
#
#     def _get_warehouse_breakdown(self, accounts):
#         """Get balance breakdown by warehouse for the accounts"""
#         if not accounts:
#             return {}, []
#
#         analytic_account_ids = self.env.context.get('analytic_account_ids', [])
#
#         if analytic_account_ids:
#             warehouses = self.env['account.analytic.account'].browse(analytic_account_ids)
#         else:
#             warehouses = self.env['account.analytic.account'].search([
#                 ('name', 'ilike', 'SSAQCO')
#             ], order='name')
#
#         if not warehouses:
#             return {}, []
#
#         # Initialize result structure
#         result = {}
#         for account in accounts:
#             result[account.id] = {}
#             for w in warehouses:
#                 result[account.id][w.id] = {
#                     'balance': 0.0,
#                     'debit': 0.0,
#                     'credit': 0.0,
#                     'name': w.name
#                 }
#
#         # Get base query components
#         tables, where_clause, where_params = self.env['account.move.line']._query_get()
#         tables = (tables or "account_move_line").replace('"', '')
#         where_clause = where_clause.strip() if where_clause else ''
#         where_params = where_params or []
#
#         # Query each warehouse separately
#         for warehouse in warehouses:
#             wheres = []
#             if where_clause:
#                 wheres.append("(%s)" % where_clause)
#
#             wheres.append(
#                 f"(analytic_distribution::text LIKE '%\"{int(warehouse.id)}\"%' OR "
#                 f"analytic_distribution::text LIKE '%\"{int(warehouse.id)}\":%')"
#             )
#
#             filters = (" AND ".join(wheres)) and " AND " + " AND ".join(wheres) or ""
#
#             request = f"""
#                 SELECT account_id,
#                        COALESCE(SUM(debit), 0) as debit,
#                        COALESCE(SUM(credit), 0) as credit,
#                        COALESCE(SUM(debit), 0) - COALESCE(SUM(credit), 0) as balance
#                 FROM {tables}
#                 WHERE account_id IN %s {filters}
#                 GROUP BY account_id
#             """
#             params = [tuple(accounts.ids)] + list(where_params)
#             self.env.cr.execute(request, tuple(params))
#
#             for row in self.env.cr.dictfetchall():
#                 acc_id = row.get('account_id')
#                 if acc_id in result:
#                     result[acc_id][warehouse.id] = {
#                         'balance': row.get('balance', 0.0),
#                         'debit': row.get('debit', 0.0),
#                         'credit': row.get('credit', 0.0),
#                         'name': warehouse.name
#                     }
#
#         return result, warehouses
#
#     @api.model
#     def _get_report_values(self, docids, data=None):
#         """Override to pass analytic information for display"""
#         result = super(ReportFinancial, self)._get_report_values(docids, data)
#
#         if not result:
#             result = {}
#
#         # Initialize default values
#         result['selected_warehouses'] = False
#         result['warehouse_display'] = 'All Warehouses'
#         result['include_combined'] = False
#         result['show_warehouse_breakdown'] = False
#
#         if data and data.get('form'):
#             form_data = data['form']
#
#             # Handle analytic account IDs
#             analytic_data = form_data.get('analytic_account_ids', [])
#             analytic_ids = []
#
#             # Normalize the many2many field data
#             if analytic_data:
#                 if isinstance(analytic_data, (list, tuple)) and analytic_data:
#                     if isinstance(analytic_data[0], (list, tuple)):
#                         # Format: [(6, 0, [ids])]
#                         analytic_ids = analytic_data[0][2] if len(analytic_data[0]) > 2 else []
#                     else:
#                         # Format: [id1, id2, ...]
#                         analytic_ids = list(analytic_data)
#
#             if analytic_ids:
#                 analytic_accounts = self.env['account.analytic.account'].browse(analytic_ids)
#                 result['selected_warehouses'] = analytic_accounts
#                 names = [acc.name for acc in analytic_accounts]
#                 result['warehouse_display'] = ', '.join(names) if names else 'All Warehouses'
#                 result['show_warehouse_breakdown'] = len(analytic_accounts) > 1
#             else:
#                 result['selected_warehouses'] = False
#                 result['warehouse_display'] = 'All Warehouses'
#                 result['show_warehouse_breakdown'] = False
#
#             result['include_combined'] = bool(form_data.get('include_combined', False))
#
#         return result


#third code for check get the separate reports
from odoo import api, models


class ReportFinancial(models.AbstractModel):
    _inherit = 'report.accounting_pdf_reports.report_financial'

    def _compute_account_balance(self, accounts):
        """Override to add analytic distribution filtering"""
        mapping = {
            'balance': "COALESCE(SUM(debit),0) - COALESCE(SUM(credit), 0) as balance",
            'debit': "COALESCE(SUM(debit), 0) as debit",
            'credit': "COALESCE(SUM(credit), 0) as credit",
        }

        res = {}
        for account in accounts:
            res[account.id] = {k: 0.0 for k in mapping.keys()}

        if not accounts:
            return res

        # Build base query parts
        tables, where_clause, where_params = self.env['account.move.line']._query_get()
        tables = (tables or "account_move_line").replace('"', '')
        where_clause = where_clause.strip() if where_clause else ''
        where_params = where_params or []

        # Build WHERE conditions
        wheres = []
        if where_clause:
            wheres.append("(%s)" % where_clause)

        # Add analytic filter if present
        analytic_account_ids = self.env.context.get('analytic_account_ids', [])
        if analytic_account_ids:
            analytic_conditions = []
            for analytic_id in analytic_account_ids:
                analytic_conditions.append(
                    f"(analytic_distribution ? '{int(analytic_id)}' OR "
                    f"analytic_distribution::text LIKE '%\"{int(analytic_id)}\"%')"
                )
            if analytic_conditions:
                wheres.append("(" + " OR ".join(analytic_conditions) + ")")

        filters = (" AND ".join(wheres)) and " AND " + " AND ".join(wheres) or ""

        request = (
                "SELECT account_id as id, " + ', '.join(mapping.values()) +
                " FROM " + tables +
                " WHERE account_id IN %s " + filters +
                " GROUP BY account_id"
        )

        params = [tuple(accounts.ids)] + list(where_params)
        self.env.cr.execute(request, tuple(params))

        for row in self.env.cr.dictfetchall():
            res[row['id']] = {
                'balance': row.get('balance', 0.0),
                'debit': row.get('debit', 0.0),
                'credit': row.get('credit', 0.0),
            }

        return res

    def _get_warehouse_breakdown(self, accounts):
        """Get balance breakdown by warehouse for the accounts"""
        if not accounts:
            return {}, []

        analytic_account_ids = self.env.context.get('analytic_account_ids', [])

        if analytic_account_ids:
            warehouses = self.env['account.analytic.account'].browse(analytic_account_ids)
        else:
            # If no specific warehouses selected, get all
            warehouses = self.env['account.analytic.account'].search([], order='name')

        if not warehouses:
            return {}, []

        # Initialize result structure
        result = {}
        for account in accounts:
            result[account.id] = {}
            for w in warehouses:
                result[account.id][w.id] = {
                    'balance': 0.0,
                    'debit': 0.0,
                    'credit': 0.0,
                    'name': w.name
                }

        # Get base query components
        tables, where_clause, where_params = self.env['account.move.line']._query_get()
        tables = (tables or "account_move_line").replace('"', '')
        where_clause = where_clause.strip() if where_clause else ''
        where_params = where_params or []

        # Query each warehouse separately
        for warehouse in warehouses:
            wheres = []
            if where_clause:
                wheres.append("(%s)" % where_clause)

            # Filter for specific warehouse only
            wheres.append(
                f"(analytic_distribution ? '{int(warehouse.id)}' OR "
                f"analytic_distribution::text LIKE '%\"{int(warehouse.id)}\"%')"
            )

            filters = (" AND ".join(wheres)) and " AND " + " AND ".join(wheres) or ""

            request = f"""
                SELECT account_id,
                       COALESCE(SUM(debit), 0) as debit,
                       COALESCE(SUM(credit), 0) as credit,
                       COALESCE(SUM(debit), 0) - COALESCE(SUM(credit), 0) as balance
                FROM {tables}
                WHERE account_id IN %s {filters}
                GROUP BY account_id
            """
            params = [tuple(accounts.ids)] + list(where_params)
            self.env.cr.execute(request, tuple(params))

            for row in self.env.cr.dictfetchall():
                acc_id = row.get('account_id')
                if acc_id in result:
                    result[acc_id][warehouse.id] = {
                        'balance': row.get('balance', 0.0),
                        'debit': row.get('debit', 0.0),
                        'credit': row.get('credit', 0.0),
                        'name': warehouse.name
                    }

        return result, warehouses

    @api.model
    def _get_report_values(self, docids, data=None):
        """Override to pass analytic information for display"""
        result = super(ReportFinancial, self)._get_report_values(docids, data)

        if not result:
            result = {}

        # Initialize default values
        result['selected_warehouses'] = False
        result['warehouse_display'] = 'All Warehouses (Combined)'
        result['include_combined'] = False
        result['show_warehouse_breakdown'] = False
        result['single_warehouse_mode'] = False

        if data and data.get('form'):
            form_data = data['form']

            # Handle analytic account IDs
            analytic_data = form_data.get('analytic_account_ids', [])
            analytic_ids = []

            # Normalize the many2many field data
            if analytic_data:
                if isinstance(analytic_data, (list, tuple)) and analytic_data:
                    if isinstance(analytic_data[0], (list, tuple)):
                        # Format: [(6, 0, [ids])]
                        analytic_ids = analytic_data[0][2] if len(analytic_data[0]) > 2 else []
                    else:
                        # Format: [id1, id2, ...]
                        analytic_ids = list(analytic_data)

            if analytic_ids:
                analytic_accounts = self.env['account.analytic.account'].browse(analytic_ids)
                result['selected_warehouses'] = analytic_accounts
                names = [acc.name for acc in analytic_accounts]

                # Determine display mode based on selection
                if len(analytic_accounts) == 1:
                    # Single warehouse selected - show only that warehouse
                    result['warehouse_display'] = f'{names[0]} (Separate Report)'
                    result['show_warehouse_breakdown'] = False
                    result['single_warehouse_mode'] = True
                else:
                    # Multiple warehouses selected
                    result['warehouse_display'] = ', '.join(names)
                    result['show_warehouse_breakdown'] = True
                    result['single_warehouse_mode'] = False
                    result['include_combined'] = bool(form_data.get('include_combined', False))
            else:
                # No warehouse selected - show all combined
                result['selected_warehouses'] = False
                result['warehouse_display'] = 'All Warehouses (Combined)'
                result['show_warehouse_breakdown'] = False
                result['single_warehouse_mode'] = False

        return result
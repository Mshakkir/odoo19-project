from odoo import api, models
import logging

_logger = logging.getLogger(__name__)


class ReportFinancial(models.AbstractModel):
    _inherit = 'report.accounting_pdf_reports.report_financial'

    def _compute_account_balance(self, accounts):
        """Override to add analytic distribution filtering"""

        # Get analytic filter from context
        analytic_account_ids = self.env.context.get('analytic_account_ids', [])

        _logger.info("=" * 80)
        _logger.info("🔍 COMPUTE ACCOUNT BALANCE - CALLED")
        _logger.info("Full Context: %s", dict(self.env.context))
        _logger.info("analytic_account_ids from context: %s", analytic_account_ids)
        _logger.info("Number of accounts to process: %s", len(accounts) if accounts else 0)

        if accounts:
            _logger.info("Sample accounts: %s", [(a.id, a.code, a.name) for a in accounts[:3]])
        _logger.info("=" * 80)

        mapping = {
            'balance': "COALESCE(SUM(debit),0) - COALESCE(SUM(credit), 0) as balance",
            'debit': "COALESCE(SUM(debit), 0) as debit",
            'credit': "COALESCE(SUM(credit), 0) as credit",
        }

        res = {}
        for account in accounts:
            res[account.id] = {k: 0.0 for k in mapping.keys()}

        if not accounts:
            _logger.warning("⚠️ No accounts provided to _compute_account_balance!")
            return res

        # Build base query parts
        tables, where_clause, where_params = self.env['account.move.line']._query_get()
        tables = (tables or "account_move_line").replace('"', '')
        where_clause = where_clause.strip() if where_clause else ''
        where_params = list(where_params) if where_params else []

        _logger.info("📝 Base query info:")
        _logger.info("  Tables: %s", tables)
        _logger.info("  Base where_clause: %s", where_clause)
        _logger.info("  Base where_params: %s", where_params)

        # Build WHERE conditions
        wheres = ["account_id IN %s"]
        params = [tuple(accounts.ids)]

        # Add base where clause
        if where_clause:
            wheres.append("(%s)" % where_clause)
            params.extend(where_params)

        # Add analytic filter if present
        if analytic_account_ids:
            _logger.info("🏢 Adding analytic filter for warehouse IDs: %s", analytic_account_ids)

            # Build analytic condition
            analytic_conditions = []
            for analytic_id in analytic_account_ids:
                # JSONB operator to check if key exists
                analytic_conditions.append(
                    f"(account_move_line.analytic_distribution ? '{str(analytic_id)}')"
                )

            if analytic_conditions:
                analytic_filter = "(" + " OR ".join(analytic_conditions) + ")"
                wheres.append(analytic_filter)
                _logger.info("  ✅ Analytic filter SQL: %s", analytic_filter)
        else:
            _logger.info("ℹ️ No analytic filter - showing ALL warehouses")

        # Construct WHERE clause
        where_str = " AND ".join(wheres)

        # Build final query
        request = (
                "SELECT account_id as id, " + ', '.join(mapping.values()) +
                " FROM " + tables +
                " WHERE " + where_str +
                " GROUP BY account_id"
        )

        _logger.info("=" * 80)
        _logger.info("📊 FINAL SQL QUERY:")
        _logger.info(request)
        _logger.info("🔢 QUERY PARAMS: %s", params)
        _logger.info("=" * 80)

        try:
            self.env.cr.execute(request, tuple(params))

            result_count = 0
            for row in self.env.cr.dictfetchall():
                res[row['id']] = {
                    'balance': row.get('balance', 0.0),
                    'debit': row.get('debit', 0.0),
                    'credit': row.get('credit', 0.0),
                }
                result_count += 1

            _logger.info("✅ Query returned %d account records", result_count)

            if result_count > 0:
                # Log first 3 results
                sample_results = list(res.items())[:3]
                for acc_id, values in sample_results:
                    account = self.env['account.account'].browse(acc_id)
                    _logger.info(
                        "  Account %s (%s): Balance=%.2f, Debit=%.2f, Credit=%.2f",
                        account.code, account.name,
                        values['balance'], values['debit'], values['credit']
                    )
            else:
                _logger.warning("⚠️ WARNING: Query returned ZERO results!")
                _logger.warning("   This means NO move lines match the filter criteria")

        except Exception as e:
            _logger.error("❌ SQL Query Error: %s", str(e))
            _logger.error("Query: %s", request)
            _logger.error("Params: %s", params)
            raise

        _logger.info("=" * 80)
        return res

    @api.model
    def _get_report_values(self, docids, data=None):
        """Override to pass analytic information for display"""

        _logger.info("=" * 80)
        _logger.info("🎯 _GET_REPORT_VALUES - CALLED (PDF Generation)")
        _logger.info("Docids: %s", docids)
        _logger.info("Data keys: %s", data.keys() if data else None)

        # Extract context and analytic IDs early
        used_context = {}
        analytic_ids = []

        if data and data.get('form'):
            form_data = data['form']
            _logger.info("📋 Form data keys: %s", form_data.keys())

            # Get context from form
            if form_data.get('used_context'):
                used_context = form_data['used_context']
                _logger.info("📦 Used context from form: %s", used_context)

            # Extract analytic account IDs
            analytic_data = form_data.get('analytic_account_ids', [])
            _logger.info("🏢 Raw analytic_data: %s (type: %s)", analytic_data, type(analytic_data))

            # Normalize the many2many field data
            if analytic_data:
                if isinstance(analytic_data, (list, tuple)) and len(analytic_data) > 0:
                    if isinstance(analytic_data[0], (list, tuple)) and len(analytic_data[0]) > 2:
                        # Format: [(6, 0, [ids])]
                        analytic_ids = analytic_data[0][2]
                    else:
                        # Format: [id1, id2, ...]
                        analytic_ids = list(analytic_data)

            _logger.info("✅ Extracted analytic_ids: %s", analytic_ids)

            # CRITICAL: Ensure analytic_ids are in the context
            if analytic_ids:
                used_context['analytic_account_ids'] = analytic_ids
                _logger.info("✅ Added analytic_ids to used_context")
            else:
                _logger.info("ℹ️ No analytic accounts selected - will show all")

        # Call parent with proper context
        if used_context:
            _logger.info("🔄 Calling parent WITH context: %s", used_context)
            result = super(ReportFinancial, self.with_context(**used_context))._get_report_values(docids, data)
        else:
            _logger.info("🔄 Calling parent WITHOUT additional context")
            result = super(ReportFinancial, self)._get_report_values(docids, data)

        if not result:
            result = {}

        # Initialize default values
        result['selected_warehouses'] = False
        result['warehouse_display'] = 'All Warehouses (Combined)'
        result['include_combined'] = False
        result['show_warehouse_breakdown'] = False
        result['single_warehouse_mode'] = False

        # Process warehouse/analytic display information
        if analytic_ids:
            analytic_accounts = self.env['account.analytic.account'].browse(analytic_ids)
            result['selected_warehouses'] = analytic_accounts
            names = [acc.name for acc in analytic_accounts]

            if len(analytic_accounts) == 1:
                # Single warehouse mode
                result['warehouse_display'] = f'📍 {names[0]} (Separate Report)'
                result['show_warehouse_breakdown'] = False
                result['single_warehouse_mode'] = True
                _logger.info("🏢 SINGLE WAREHOUSE MODE: %s", names[0])
            else:
                # Multiple warehouses mode
                result['warehouse_display'] = f'📦 {", ".join(names)} (Combined)'
                result['show_warehouse_breakdown'] = True
                result['single_warehouse_mode'] = False
                if data and data.get('form'):
                    result['include_combined'] = bool(data['form'].get('include_combined', False))
                _logger.info("🏢 MULTIPLE WAREHOUSE MODE: %s", ", ".join(names))
        else:
            # All warehouses mode
            result['warehouse_display'] = '🌍 All Warehouses (Combined)'
            _logger.info("🌍 ALL WAREHOUSES MODE")

        _logger.info("📊 Final result keys: %s", result.keys())
        _logger.info("=" * 80)

        return result




















# from odoo import api, models
# import logging
#
# _logger = logging.getLogger(__name__)
#
#
# class ReportFinancial(models.AbstractModel):
#     _inherit = 'report.accounting_pdf_reports.report_financial'
#
#     def _compute_account_balance(self, accounts):
#         """Override to add analytic distribution filtering"""
#
#         # DEBUG: Check context
#         analytic_account_ids = self.env.context.get('analytic_account_ids', [])
#         _logger.info("=" * 80)
#         _logger.info("COMPUTE ACCOUNT BALANCE - DEBUG INFO")
#         _logger.info("Context analytic_account_ids: %s", analytic_account_ids)
#         _logger.info("Full context keys: %s", list(self.env.context.keys()))
#         _logger.info("=" * 80)
#
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
#         _logger.info("Base where_clause: %s", where_clause)
#         _logger.info("Base where_params: %s", where_params)
#
#         # Build WHERE conditions
#         wheres = []
#         if where_clause:
#             wheres.append("(%s)" % where_clause)
#
#         # Add analytic filter if present
#         if analytic_account_ids:
#             _logger.info("Adding analytic filter for IDs: %s", analytic_account_ids)
#             analytic_conditions = []
#             for analytic_id in analytic_account_ids:
#                 # Use JSONB operators for better accuracy
#                 analytic_conditions.append(
#                     f"(analytic_distribution ? '{int(analytic_id)}')"
#                 )
#             if analytic_conditions:
#                 analytic_filter = "(" + " OR ".join(analytic_conditions) + ")"
#                 wheres.append(analytic_filter)
#                 _logger.info("Analytic filter added: %s", analytic_filter)
#         else:
#             _logger.warning("NO ANALYTIC FILTER - Will show all data!")
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
#
#         _logger.info("FINAL SQL QUERY:")
#         _logger.info(request)
#         _logger.info("QUERY PARAMS: %s", params)
#
#         self.env.cr.execute(request, tuple(params))
#
#         result_count = 0
#         for row in self.env.cr.dictfetchall():
#             res[row['id']] = {
#                 'balance': row.get('balance', 0.0),
#                 'debit': row.get('debit', 0.0),
#                 'credit': row.get('credit', 0.0),
#             }
#             result_count += 1
#
#         _logger.info("Query returned %s account records", result_count)
#         _logger.info("=" * 80)
#
#         return res
#
#
#     @api.model
#     def _get_report_values(self, docids, data=None):
#         """Override to pass analytic information for display"""
#
#         # DEBUG: Log incoming data
#         _logger.info("=" * 80)
#         _logger.info("GET REPORT VALUES - DEBUG INFO")
#         _logger.info("Docids: %s", docids)
#         _logger.info("Data keys: %s", data.keys() if data else "No data")
#         if data and data.get('form'):
#             _logger.info("Form analytic_account_ids: %s", data['form'].get('analytic_account_ids'))
#             _logger.info("Form used_context: %s", data['form'].get('used_context', {}).get('analytic_account_ids'))
#         _logger.info("Current context analytic_account_ids: %s", self.env.context.get('analytic_account_ids'))
#         _logger.info("=" * 80)
#
#         # Call parent with context
#         if data and data.get('form') and data['form'].get('used_context'):
#             used_context = data['form']['used_context']
#             result = super(ReportFinancial, self.with_context(**used_context))._get_report_values(docids, data)
#         else:
#             result = super(ReportFinancial, self)._get_report_values(docids, data)
#
#         if not result:
#             result = {}
#
#         # Initialize default values
#         result['selected_warehouses'] = False
#         result['warehouse_display'] = 'All Warehouses (Combined)'
#         result['include_combined'] = False
#         result['show_warehouse_breakdown'] = False
#         result['single_warehouse_mode'] = False
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
#             _logger.info("Normalized analytic_ids: %s", analytic_ids)
#
#             if analytic_ids:
#                 analytic_accounts = self.env['account.analytic.account'].browse(analytic_ids)
#                 result['selected_warehouses'] = analytic_accounts
#                 names = [acc.name for acc in analytic_accounts]
#
#                 # Determine display mode based on selection
#                 if len(analytic_accounts) == 1:
#                     # Single warehouse selected - show only that warehouse
#                     result['warehouse_display'] = f'{names[0]} (Separate Report)'
#                     result['show_warehouse_breakdown'] = False
#                     result['single_warehouse_mode'] = True
#                     _logger.info("SINGLE WAREHOUSE MODE: %s", names[0])
#                 else:
#                     # Multiple warehouses selected
#                     result['warehouse_display'] = ', '.join(names)
#                     result['show_warehouse_breakdown'] = True
#                     result['single_warehouse_mode'] = False
#                     result['include_combined'] = bool(form_data.get('include_combined', False))
#                     _logger.info("MULTIPLE WAREHOUSE MODE: %s", names)
#             else:
#                 # No warehouse selected - show all combined
#                 result['selected_warehouses'] = False
#                 result['warehouse_display'] = 'All Warehouses (Combined)'
#                 result['show_warehouse_breakdown'] = False
#                 result['single_warehouse_mode'] = False
#                 _logger.info("ALL WAREHOUSES MODE")
#
#         _logger.info("=" * 80)
#         return result















# from odoo import api, models, fields
# import logging
#
# _logger = logging.getLogger(__name__)
#
#
# class ReportFinancial(models.AbstractModel):
#     _inherit = 'report.accounting_pdf_reports.report_financial'
#
#     def _compute_account_balance(self, accounts):
#         """Override to add analytic distribution filtering"""
#
#         # DEBUG: Check context
#         analytic_account_ids = self.env.context.get('analytic_account_ids', [])
#         _logger.info("=" * 80)
#         _logger.info("COMPUTE ACCOUNT BALANCE - DEBUG INFO")
#         _logger.info("Context analytic_account_ids: %s", analytic_account_ids)
#         _logger.info("Full context keys: %s", list(self.env.context.keys()))
#         _logger.info("=" * 80)
#
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
#         _logger.info("Base where_clause: %s", where_clause)
#         _logger.info("Base where_params: %s", where_params)
#
#         # Build WHERE conditions
#         wheres = []
#         if where_clause:
#             wheres.append("(%s)" % where_clause)
#
#         # Add analytic filter if present
#         if analytic_account_ids:
#             _logger.info("Adding analytic filter for IDs: %s", analytic_account_ids)
#             analytic_conditions = []
#             for analytic_id in analytic_account_ids:
#                 # Use JSONB operators for better accuracy
#                 analytic_conditions.append(
#                     f"(analytic_distribution ? '{int(analytic_id)}')"
#                 )
#             if analytic_conditions:
#                 analytic_filter = "(" + " OR ".join(analytic_conditions) + ")"
#                 wheres.append(analytic_filter)
#                 _logger.info("Analytic filter added: %s", analytic_filter)
#         else:
#             _logger.warning("NO ANALYTIC FILTER - Will show all data!")
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
#
#         _logger.info("FINAL SQL QUERY:")
#         _logger.info(request)
#         _logger.info("QUERY PARAMS: %s", params)
#
#         self.env.cr.execute(request, tuple(params))
#
#         result_count = 0
#         for row in self.env.cr.dictfetchall():
#             res[row['id']] = {
#                 'balance': row.get('balance', 0.0),
#                 'debit': row.get('debit', 0.0),
#                 'credit': row.get('credit', 0.0),
#             }
#             result_count += 1
#
#         _logger.info("Query returned %s account records", result_count)
#         _logger.info("=" * 80)
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
#             # If no specific warehouses selected, get all
#             warehouses = self.env['account.analytic.account'].search([], order='name')
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
#             # Filter for specific warehouse only using JSONB operator
#             wheres.append(f"(analytic_distribution ? '{int(warehouse.id)}')")
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
#
#         # DEBUG: Log incoming data
#         _logger.info("=" * 80)
#         _logger.info("GET REPORT VALUES - DEBUG INFO")
#         _logger.info("Docids: %s", docids)
#         _logger.info("Data keys: %s", data.keys() if data else "No data")
#         if data and data.get('form'):
#             _logger.info("Form analytic_account_ids: %s", data['form'].get('analytic_account_ids'))
#             _logger.info("Form used_context: %s", data['form'].get('used_context', {}).get('analytic_account_ids'))
#         _logger.info("Current context analytic_account_ids: %s", self.env.context.get('analytic_account_ids'))
#         _logger.info("=" * 80)
#
#         # Call parent with context
#         if data and data.get('form') and data['form'].get('used_context'):
#             used_context = data['form']['used_context']
#             result = super(ReportFinancial, self.with_context(**used_context))._get_report_values(docids, data)
#         else:
#             result = super(ReportFinancial, self)._get_report_values(docids, data)
#
#         if not result:
#             result = {}
#
#         # Initialize default values
#         result['selected_warehouses'] = False
#         result['warehouse_display'] = 'All Warehouses (Combined)'
#         result['include_combined'] = False
#         result['show_warehouse_breakdown'] = False
#         result['single_warehouse_mode'] = False
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
#             _logger.info("Normalized analytic_ids: %s", analytic_ids)
#
#             if analytic_ids:
#                 analytic_accounts = self.env['account.analytic.account'].browse(analytic_ids)
#                 result['selected_warehouses'] = analytic_accounts
#                 names = [acc.name for acc in analytic_accounts]
#
#                 # Determine display mode based on selection
#                 if len(analytic_accounts) == 1:
#                     # Single warehouse selected - show only that warehouse
#                     result['warehouse_display'] = f'{names[0]} (Separate Report)'
#                     result['show_warehouse_breakdown'] = False
#                     result['single_warehouse_mode'] = True
#                     _logger.info("SINGLE WAREHOUSE MODE: %s", names[0])
#                 else:
#                     # Multiple warehouses selected
#                     result['warehouse_display'] = ', '.join(names)
#                     result['show_warehouse_breakdown'] = True
#                     result['single_warehouse_mode'] = False
#                     result['include_combined'] = bool(form_data.get('include_combined', False))
#                     _logger.info("MULTIPLE WAREHOUSE MODE: %s", names)
#             else:
#                 # No warehouse selected - show all combined
#                 result['selected_warehouses'] = False
#                 result['warehouse_display'] = 'All Warehouses (Combined)'
#                 result['show_warehouse_breakdown'] = False
#                 result['single_warehouse_mode'] = False
#                 _logger.info("ALL WAREHOUSES MODE")
#
#         _logger.info("=" * 80)
#         return result
#
#
# class AccountFinancialReportLine(models.Model):
#     """Transient model to display account lines in tree view"""
#     _name = 'account.financial.report.line'
#     _description = 'Financial Report Line'
#     _order = 'sequence, code'
#
#     name = fields.Char(string='Account', required=True)
#     code = fields.Char(string='Code')
#     account_id = fields.Many2one('account.account', string='Account')
#     debit = fields.Float(string='Debit', digits='Account')
#     credit = fields.Float(string='Credit', digits='Account')
#     balance = fields.Float(string='Balance', digits='Account')
#     report_type = fields.Selection([
#         ('balance_sheet', 'Balance Sheet'),
#         ('profit_loss', 'Profit & Loss')
#     ], string='Report Type')
#     sequence = fields.Integer(string='Sequence', default=10)
#
#     # Store filter context for ledger viewing
#     date_from = fields.Date(string='Date From')
#     date_to = fields.Date(string='Date To')
#     analytic_account_ids = fields.Many2many('account.analytic.account', string='Warehouses')
#     target_move = fields.Selection([
#         ('posted', 'All Posted Entries'),
#         ('all', 'All Entries')
#     ], string='Target Moves')
#
#     def action_view_ledger(self):
#         """Open ledger view for the selected account with filters"""
#         self.ensure_one()
#
#         if not self.account_id:
#             return
#
#         # Build domain for ledger filtering
#         domain = [('account_id', '=', self.account_id.id)]
#
#         if self.date_from:
#             domain.append(('date', '>=', self.date_from))
#         if self.date_to:
#             domain.append(('date', '<=', self.date_to))
#
#         # Add target move filter
#         if self.target_move == 'posted':
#             domain.append(('move_id.state', '=', 'posted'))
#
#         # Add analytic filter if present
#         if self.analytic_account_ids:
#             analytic_domain = []
#             for analytic in self.analytic_account_ids:
#                 analytic_domain.append(('analytic_distribution', '?', str(analytic.id)))
#             if len(analytic_domain) > 1:
#                 domain.append('|' * (len(analytic_domain) - 1))
#             domain.extend(analytic_domain)
#
#         # Prepare context
#         ctx = dict(self.env.context or {})
#         ctx.update({
#             'search_default_group_by_account': 1,
#             'search_default_posted': 1 if self.target_move == 'posted' else 0,
#         })
#
#         return {
#             'name': f'Ledger - {self.code} {self.name}',
#             'type': 'ir.actions.act_window',
#             'res_model': 'account.move.line',
#             'view_mode': 'tree,form',
#             'domain': domain,
#             'context': ctx,
#             'target': 'current',
#         }
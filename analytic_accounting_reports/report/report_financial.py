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
        _logger.info("🔍 _compute_account_balance CALLED")
        _logger.info("Context analytic_account_ids: %s", analytic_account_ids)
        _logger.info("Number of accounts: %s", len(accounts) if accounts else 0)

        if accounts:
            _logger.info("Sample accounts: %s", [(a.code, a.name) for a in accounts[:3]])
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
            return res

        # Build base query parts
        tables, where_clause, where_params = self.env['account.move.line']._query_get()
        tables = (tables or "account_move_line").replace('"', '')
        where_clause = where_clause.strip() if where_clause else ''
        where_params = list(where_params) if where_params else []

        _logger.info("Base tables: %s", tables)
        _logger.info("Base where_clause: %s", where_clause)

        # Build WHERE conditions
        wheres = ["account_id IN %s"]
        params = [tuple(accounts.ids)]

        if where_clause:
            wheres.append("(%s)" % where_clause)
            params.extend(where_params)

        # Add analytic filter ONLY if analytic_account_ids are provided
        if analytic_account_ids:
            _logger.info("🏢 APPLYING analytic filter for IDs: %s", analytic_account_ids)

            # First, let's check what data exists
            test_query = f"SELECT DISTINCT analytic_distribution FROM {tables} WHERE account_id IN %s LIMIT 10"
            self.env.cr.execute(test_query, (tuple(accounts.ids),))
            sample_distributions = [r[0] for r in self.env.cr.fetchall() if r[0]]
            _logger.info("📊 Sample analytic_distributions in database: %s", sample_distributions)

            analytic_conditions = []
            for analytic_id in analytic_account_ids:
                # Try both string and integer keys
                analytic_conditions.append(
                    f"(account_move_line.analytic_distribution ? '{str(analytic_id)}')"
                )

            if analytic_conditions:
                analytic_filter = "(" + " OR ".join(analytic_conditions) + ")"
                wheres.append(analytic_filter)
                _logger.info("✅ Analytic filter SQL: %s", analytic_filter)
        else:
            _logger.info("ℹ️  NO analytic filter - showing ALL data")

        where_str = " AND ".join(wheres)
        request = (
                "SELECT account_id as id, " + ', '.join(mapping.values()) +
                " FROM " + tables +
                " WHERE " + where_str +
                " GROUP BY account_id"
        )

        _logger.info("=" * 80)
        _logger.info("📊 FINAL SQL:")
        _logger.info(request)
        _logger.info("Params: %s", params)
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

            _logger.info("✅ Query returned %d accounts with data", result_count)

            if result_count > 0:
                # Show first 3 results
                for i, (acc_id, values) in enumerate(list(res.items())[:3]):
                    if values['balance'] != 0 or values['debit'] != 0 or values['credit'] != 0:
                        account = self.env['account.account'].browse(acc_id)
                        _logger.info("  %s (%s): Bal=%.2f, Dr=%.2f, Cr=%.2f",
                                     account.code, account.name,
                                     values['balance'], values['debit'], values['credit'])
            else:
                _logger.warning("⚠️  ZERO results returned!")
                _logger.warning("   Either no data exists OR filter is too restrictive")

        except Exception as e:
            _logger.error("❌ SQL Error: %s", str(e))
            _logger.error("Query: %s", request)
            _logger.error("Params: %s", params)
            raise

        _logger.info("=" * 80)
        return res

    @api.model
    def _get_report_values(self, docids, data=None):
        """Override to pass analytic information for display"""

        _logger.info("=" * 80)
        _logger.info("🎯 _get_report_values CALLED (PDF Generation)")
        _logger.info("Docids: %s", docids)
        _logger.info("Current context: %s", dict(self.env.context))
        _logger.info("=" * 80)

        # Extract context and analytic IDs
        used_context = {}
        analytic_ids = []

        if data and data.get('form'):
            form_data = data['form']
            _logger.info("📋 Form data keys: %s", form_data.keys())

            # Get context from form
            if form_data.get('used_context'):
                used_context = form_data['used_context']
                _logger.info("📦 used_context from form: %s", used_context)

            # Extract analytic account IDs
            analytic_data = form_data.get('analytic_account_ids', [])
            _logger.info("🏢 Raw analytic_account_ids: %s (type: %s)", analytic_data, type(analytic_data))

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

            # Ensure analytic_ids are in the context
            if analytic_ids:
                used_context['analytic_account_ids'] = analytic_ids
                _logger.info("✅ Added to context")

        # Call parent with proper context
        if used_context and analytic_ids:
            _logger.info("🔄 Calling parent WITH context")
            result = super(ReportFinancial, self.with_context(**used_context))._get_report_values(docids, data)
        else:
            _logger.info("🔄 Calling parent WITHOUT additional context")
            result = super(ReportFinancial, self)._get_report_values(docids, data)

        if not result:
            result = {}

        # Initialize default values
        result['selected_warehouses'] = False
        result['warehouse_display'] = 'All Warehouses (Combined)'
        result['single_warehouse_mode'] = False

        # Process warehouse/analytic display information
        if analytic_ids:
            analytic_accounts = self.env['account.analytic.account'].browse(analytic_ids)
            result['selected_warehouses'] = analytic_accounts
            names = [acc.name for acc in analytic_accounts]

            if len(analytic_accounts) == 1:
                result['warehouse_display'] = f'{names[0]} (Separate Report)'
                result['single_warehouse_mode'] = True
                _logger.info("🏢 SINGLE WAREHOUSE MODE: %s", names[0])
            else:
                result['warehouse_display'] = f'{", ".join(names)}'
                _logger.info("🏢 MULTIPLE WAREHOUSES: %s", names)
        else:
            _logger.info("🌍 ALL WAREHOUSES MODE")

        _logger.info("📊 warehouse_display: %s", result['warehouse_display'])
        _logger.info("=" * 80)

        return result
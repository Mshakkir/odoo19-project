# from odoo import api, fields, models
# import logging
#
# _logger = logging.getLogger(__name__)
#
#
# class AccountBalanceReport(models.TransientModel):
#     """Extend Trial Balance wizard to add analytic account filter."""
#
#     _inherit = 'account.balance.report'
#
#     analytic_account_ids = fields.Many2many(
#         'account.analytic.account',
#         'account_trial_balance_analytic_warehouse_rel',
#         'balance_report_id',
#         'analytic_account_id',
#         string='Analytic Accounts (Warehouses)',
#         help='Filter Trial Balance by warehouse analytic accounts. '
#              'Leave empty to show combined report for all warehouses.'
#     )
#
#     def _print_report(self, data):
#         """Override to pass analytic filter to report."""
#         # Get form data including analytic accounts
#         data = self.pre_print_report(data)
#
#         # Add analytic account IDs to data
#         if self.analytic_account_ids:
#             data['form']['analytic_account_ids'] = self.analytic_account_ids.ids
#             _logger.info(f"Trial Balance: Filtering by analytic accounts {self.analytic_account_ids.ids}")
#         else:
#             data['form']['analytic_account_ids'] = []
#             _logger.info("Trial Balance: No analytic filter - showing all warehouses")
#
#         records = self.env[data['model']].browse(data.get('ids', []))
#         return self.env.ref('accounting_pdf_reports.action_report_trial_balance').report_action(
#             records, data=data
#         )
#
#
# class ReportTrialBalance(models.AbstractModel):
#     """Extend Trial Balance report to filter by analytic accounts."""
#
#     _inherit = 'report.accounting_pdf_reports.report_trialbalance'
#
#     def _get_accounts(self, accounts, display_account):
#         """
#         Override to add analytic account filtering using analytic_distribution.
#
#         In Odoo 19, analytic accounts are stored in JSON field 'analytic_distribution'
#         Format: {"account_id": percentage} e.g., {"2": 100.0, "3": 50.0}
#
#         SIMPLIFIED VERSION: Uses Python filtering instead of complex SQL
#         """
#         # Get analytic filter from context
#         analytic_account_ids = self.env.context.get('analytic_account_ids')
#
#         if not analytic_account_ids:
#             # No filter - use parent method (show all)
#             _logger.info("No analytic filter - using parent method")
#             return super()._get_accounts(accounts, display_account)
#
#         # Extract IDs if it's a recordset
#         if hasattr(analytic_account_ids, 'ids'):
#             analytic_ids = analytic_account_ids.ids
#         else:
#             analytic_ids = list(analytic_account_ids) if isinstance(analytic_account_ids, (list, tuple)) else [
#                 analytic_account_ids]
#
#         _logger.info(f"=== TRIAL BALANCE ANALYTIC FILTER ACTIVE ===")
#         _logger.info(f"Filtering by analytic account IDs: {analytic_ids}")
#
#         # Build SQL query WITHOUT analytic filter first (get all lines)
#         tables, where_clause, where_params = self.env['account.move.line']._query_get()
#         tables = tables.replace('"', '') or 'account_move_line'
#
#         wheres = []
#         if where_clause.strip():
#             wheres.append(where_clause.strip())
#         filters = " AND ".join(wheres) if wheres else "1=1"
#
#         # Simple SQL: Get all move lines for the accounts
#         request = f"""
#             SELECT
#                 id,
#                 account_id,
#                 debit,
#                 credit,
#                 analytic_distribution
#             FROM {tables}
#             WHERE account_id IN %s AND {filters}
#         """
#
#         params = (tuple(accounts.ids),) + tuple(where_params)
#
#         _logger.info(f"Executing SQL query with {len(accounts)} accounts")
#         _logger.info(f"SQL: {request}")
#
#         self.env.cr.execute(request, params)
#         all_lines = self.env.cr.dictfetchall()
#
#         _logger.info(f"Total move lines found: {len(all_lines)}")
#
#         # Filter and calculate in Python
#         account_result = {}
#
#         for line in all_lines:
#             account_id = line['account_id']
#             analytic_dist = line['analytic_distribution']
#
#             # Check if this line has any of our analytic accounts
#             if not analytic_dist:
#                 _logger.debug(f"Line {line['id']}: No analytic distribution, skipping")
#                 continue
#
#             # Calculate percentage for our analytic accounts
#             percentage = 0.0
#             for analytic_id in analytic_ids:
#                 analytic_id_str = str(analytic_id)
#                 if analytic_id_str in analytic_dist:
#                     percentage += float(analytic_dist[analytic_id_str])
#                     _logger.debug(
#                         f"Line {line['id']}: Found analytic {analytic_id_str} with {analytic_dist[analytic_id_str]}%")
#
#             if percentage == 0:
#                 continue
#
#             # Calculate proportional amounts
#             proportional_debit = line['debit'] * (percentage / 100.0)
#             proportional_credit = line['credit'] * (percentage / 100.0)
#
#             _logger.debug(f"Line {line['id']}: Debit {line['debit']} * {percentage}% = {proportional_debit}")
#
#             # Add to account totals
#             if account_id not in account_result:
#                 account_result[account_id] = {'debit': 0.0, 'credit': 0.0, 'balance': 0.0}
#
#             account_result[account_id]['debit'] += proportional_debit
#             account_result[account_id]['credit'] += proportional_credit
#             account_result[account_id]['balance'] = account_result[account_id]['debit'] - account_result[account_id][
#                 'credit']
#
#         _logger.info(f"Accounts with filtered transactions: {len(account_result)}")
#         for acc_id, values in account_result.items():
#             _logger.info(
#                 f"  Account {acc_id}: Debit={values['debit']:.2f}, Credit={values['credit']:.2f}, Balance={values['balance']:.2f}")
#
#         # Build result list
#         account_res = []
#         for account in accounts:
#             res = dict.fromkeys(['credit', 'debit', 'balance'], 0.0)
#             currency = account.currency_id or self.env.company.currency_id
#
#             res.update({
#                 'code': account.code,
#                 'name': account.name,
#             })
#
#             if account.id in account_result:
#                 res['debit'] = account_result[account.id]['debit']
#                 res['credit'] = account_result[account.id]['credit']
#                 res['balance'] = account_result[account.id]['balance']
#
#             # Apply display filter
#             if display_account == 'all':
#                 account_res.append(res)
#             elif display_account == 'not_zero' and not currency.is_zero(res['balance']):
#                 account_res.append(res)
#             elif display_account == 'movement' and (
#                     not currency.is_zero(res['debit']) or not currency.is_zero(res['credit'])
#             ):
#                 account_res.append(res)
#
#         _logger.info(f"Accounts in final report: {len(account_res)}")
#         _logger.info(f"=== END TRIAL BALANCE ANALYTIC FILTER ===")
#
#         return account_res
#
#     @api.model
#     def _get_report_values(self, docids, data=None):
#         """Override to pass analytic accounts to context and display them in report."""
#         # Get base report values from parent
#         res = super()._get_report_values(docids, data=data)
#
#         # Add analytic account names for display in report header
#         if data and data.get('form', {}).get('analytic_account_ids'):
#             analytic_ids = data['form']['analytic_account_ids']
#             analytic_accounts = self.env['account.analytic.account'].browse(analytic_ids)
#             res['analytic_accounts'] = [acc.name for acc in analytic_accounts]
#             _logger.info(f"Report will show analytic accounts: {res['analytic_accounts']}")
#         else:
#             res['analytic_accounts'] = []
#
#         return res
from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)


class AccountBalanceReport(models.TransientModel):
    """Extend Trial Balance wizard to add analytic account filter."""

    _inherit = 'account.balance.report'

    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        'account_trial_balance_analytic_warehouse_rel',
        'balance_report_id',
        'analytic_account_id',
        string='Analytic Accounts (Warehouses)',
        help='Filter Trial Balance by warehouse analytic accounts. '
             'Leave empty to show combined report for all warehouses.'
    )

    def _print_report(self, data):
        """Override to pass analytic filter to report."""
        data = self.pre_print_report(data)

        if self.analytic_account_ids:
            data['form']['analytic_account_ids'] = self.analytic_account_ids.ids
            _logger.info(f"Trial Balance: Filtering by analytic accounts {self.analytic_account_ids.ids}")
        else:
            data['form'].pop('analytic_account_ids', None)
            _logger.info("Trial Balance: No analytic filter - showing all warehouses")

        records = self.env[data['model']].browse(data.get('ids', []))
        return self.env.ref('accounting_pdf_reports.action_report_trial_balance').report_action(
            records, data=data
        )


class ReportTrialBalance(models.AbstractModel):
    """Extend Trial Balance report to filter by analytic accounts."""

    _inherit = 'report.accounting_pdf_reports.report_trialbalance'

    def _get_accounts(self, accounts, display_account):
        """
        Complete rewrite - does NOT call super() to avoid parent method issues.
        Handles both filtered and unfiltered cases in unified logic.
        """
        analytic_account_ids = self.env.context.get('analytic_account_ids')

        # Check if we have analytic filter
        has_analytic_filter = False
        analytic_ids = []

        if analytic_account_ids:
            if hasattr(analytic_account_ids, 'ids'):
                analytic_ids = analytic_account_ids.ids
            elif isinstance(analytic_account_ids, (list, tuple)):
                analytic_ids = list(analytic_account_ids)
            else:
                analytic_ids = [analytic_account_ids]

            if analytic_ids and len(analytic_ids) > 0:
                has_analytic_filter = True

        _logger.info("=" * 80)
        if has_analytic_filter:
            _logger.info(f"ANALYTIC FILTER ACTIVE: {analytic_ids}")
        else:
            _logger.info("NO ANALYTIC FILTER - Showing ALL account movements")
        _logger.info(f"Display account setting: {display_account}")
        _logger.info(f"Processing {len(accounts)} accounts")

        # Log date range from context
        date_from = self.env.context.get('date_from')
        date_to = self.env.context.get('date_to')
        _logger.info(f"Date range: {date_from} to {date_to}")
        _logger.info("=" * 80)

        # Get SQL query components from context
        tables, where_clause, where_params = self.env['account.move.line']._query_get()
        tables = tables.replace('"', '') or 'account_move_line'

        wheres = []
        if where_clause.strip():
            wheres.append(where_clause.strip())
        filters = " AND ".join(wheres) if wheres else "1=1"

        _logger.info(f"SQL WHERE clause: {filters}")
        _logger.info(f"SQL WHERE params: {where_params}")

        # Query to get all move lines
        request = f"""
            SELECT 
                id,
                account_id,
                debit,
                credit,
                analytic_distribution,
                date
            FROM {tables}
            WHERE account_id IN %s AND {filters}
        """

        params = (tuple(accounts.ids),) + tuple(where_params)

        _logger.info("Executing SQL query...")
        _logger.debug(f"Full SQL: {request}")
        _logger.debug(f"Full params: {params}")

        self.env.cr.execute(request, params)
        all_lines = self.env.cr.dictfetchall()

        _logger.info(f"✓ Found {len(all_lines)} move lines in database")

        if len(all_lines) == 0:
            _logger.warning("⚠️  NO MOVE LINES FOUND!")
            _logger.warning(f"   This usually means:")
            _logger.warning(f"   1. No transactions in date range {date_from} to {date_to}")
            _logger.warning(f"   2. No posted transactions (if target_move='posted')")
            _logger.warning(f"   3. Wrong journal selection")
            _logger.warning("=" * 80)
            return []

        # Calculate account totals
        account_result = {}
        lines_included = 0
        lines_excluded_no_analytic = 0
        lines_excluded_no_match = 0

        for line in all_lines:
            account_id = line['account_id']
            analytic_dist = line['analytic_distribution']

            # Determine what percentage to include
            percentage = 100.0  # Default: include full amount

            if has_analytic_filter:
                # We have a filter - only include if line matches
                if not analytic_dist:
                    lines_excluded_no_analytic += 1
                    _logger.debug(f"Line {line['id']}: Excluded - no analytic distribution")
                    continue  # Skip lines without analytic distribution

                # Calculate matching percentage
                percentage = 0.0
                for analytic_id in analytic_ids:
                    analytic_id_str = str(analytic_id)
                    if analytic_id_str in analytic_dist:
                        percentage += float(analytic_dist[analytic_id_str])
                        _logger.debug(
                            f"Line {line['id']}: Matched analytic {analytic_id_str} = {analytic_dist[analytic_id_str]}%")

                if percentage == 0:
                    lines_excluded_no_match += 1
                    _logger.debug(f"Line {line['id']}: Excluded - no matching analytic accounts")
                    continue  # No match, skip this line

            lines_included += 1

            # Calculate amounts (proportional if filtered)
            proportional_debit = line['debit'] * (percentage / 100.0)
            proportional_credit = line['credit'] * (percentage / 100.0)

            _logger.debug(
                f"Line {line['id']}: Debit={line['debit']}, Credit={line['credit']}, Percentage={percentage}%")

            # Add to account totals
            if account_id not in account_result:
                account_result[account_id] = {'debit': 0.0, 'credit': 0.0, 'balance': 0.0}

            account_result[account_id]['debit'] += proportional_debit
            account_result[account_id]['credit'] += proportional_credit
            account_result[account_id]['balance'] = (
                    account_result[account_id]['debit'] - account_result[account_id]['credit']
            )

        _logger.info(f"Lines included in calculation: {lines_included}")
        if has_analytic_filter:
            _logger.info(f"Lines excluded (no analytic): {lines_excluded_no_analytic}")
            _logger.info(f"Lines excluded (no match): {lines_excluded_no_match}")
        _logger.info(f"Accounts with transactions: {len(account_result)}")

        # Show sample of results
        for acc_id in list(account_result.keys())[:5]:
            vals = account_result[acc_id]
            _logger.info(
                f"  Account {acc_id}: Debit={vals['debit']:.2f}, Credit={vals['credit']:.2f}, Balance={vals['balance']:.2f}")

        # Build result list
        account_res = []
        for account in accounts:
            res = dict.fromkeys(['credit', 'debit', 'balance'], 0.0)
            currency = account.currency_id or self.env.company.currency_id

            res.update({
                'code': account.code,
                'name': account.name,
            })

            if account.id in account_result:
                res['debit'] = account_result[account.id]['debit']
                res['credit'] = account_result[account.id]['credit']
                res['balance'] = account_result[account.id]['balance']

            # Apply display filter
            if display_account == 'all':
                account_res.append(res)
            elif display_account == 'not_zero' and not currency.is_zero(res['balance']):
                account_res.append(res)
            elif display_account == 'movement' and (
                    not currency.is_zero(res['debit']) or not currency.is_zero(res['credit'])
            ):
                account_res.append(res)

        _logger.info(f"✓ Accounts in final report (after '{display_account}' filter): {len(account_res)}")
        _logger.info("=" * 80)

        return account_res

    @api.model
    def _get_report_values(self, docids, data=None):
        """Override to pass analytic accounts to context and display them in report."""
        _logger.info("=" * 80)
        _logger.info("_get_report_values called")
        _logger.info(f"Display account: {data.get('form', {}).get('display_account') if data else 'N/A'}")
        _logger.info(f"Date from: {data.get('form', {}).get('date_from') if data else 'N/A'}")
        _logger.info(f"Date to: {data.get('form', {}).get('date_to') if data else 'N/A'}")
        _logger.info("=" * 80)

        # Get base report values from parent
        res = super()._get_report_values(docids, data=data)

        # Add analytic account names for display in report header
        analytic_ids = data.get('form', {}).get('analytic_account_ids') if data else None

        if analytic_ids and len(analytic_ids) > 0:
            analytic_accounts = self.env['account.analytic.account'].browse(analytic_ids)
            res['analytic_accounts'] = [acc.name for acc in analytic_accounts]
            _logger.info(f"Report header will show analytic filter: {res['analytic_accounts']}")
        else:
            res['analytic_accounts'] = []
            _logger.info("Report header: No analytic filter")

        _logger.info(f"✓ Final result contains {len(res.get('Accounts', []))} accounts")
        _logger.info("=" * 80)

        return res
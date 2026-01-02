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
        # Get form data including analytic accounts
        data = self.pre_print_report(data)

        # Add analytic account IDs to data
        if self.analytic_account_ids:
            data['form']['analytic_account_ids'] = self.analytic_account_ids.ids
            _logger.info(f"Trial Balance: Filtering by analytic accounts {self.analytic_account_ids.ids}")
        else:
            data['form']['analytic_account_ids'] = []
            _logger.info("Trial Balance: No analytic filter - showing all warehouses")

        records = self.env[data['model']].browse(data.get('ids', []))
        return self.env.ref('accounting_pdf_reports.action_report_trial_balance').report_action(
            records, data=data
        )


class ReportTrialBalance(models.AbstractModel):
    """Extend Trial Balance report to filter by analytic accounts."""

    _inherit = 'report.accounting_pdf_reports.report_trialbalance'

    # def _get_accounts(self, accounts, display_account):
    #     """
    #     Override to add analytic account filtering using analytic_distribution.
    #
    #     In Odoo 19, analytic accounts are stored in JSON field 'analytic_distribution'
    #     Format: {"account_id": percentage} e.g., {"2": 100.0, "3": 50.0}
    #
    #     SIMPLIFIED VERSION: Uses Python filtering instead of complex SQL
    #     """
    #     # Get analytic filter from context
    #     analytic_account_ids = self.env.context.get('analytic_account_ids')
    #
    #     if not analytic_account_ids:
    #         # No filter - use parent method (show all)
    #         _logger.info("No analytic filter - using parent method")
    #         return super()._get_accounts(accounts, display_account)
    #
    #     # Extract IDs if it's a recordset
    #     if hasattr(analytic_account_ids, 'ids'):
    #         analytic_ids = analytic_account_ids.ids
    #     else:
    #         analytic_ids = list(analytic_account_ids) if isinstance(analytic_account_ids, (list, tuple)) else [
    #             analytic_account_ids]
    #
    #     _logger.info(f"=== TRIAL BALANCE ANALYTIC FILTER ACTIVE ===")
    #     _logger.info(f"Filtering by analytic account IDs: {analytic_ids}")
    #
    #     # Build SQL query WITHOUT analytic filter first (get all lines)
    #     tables, where_clause, where_params = self.env['account.move.line']._query_get()
    #     tables = tables.replace('"', '') or 'account_move_line'
    #
    #     wheres = []
    #     if where_clause.strip():
    #         wheres.append(where_clause.strip())
    #     filters = " AND ".join(wheres) if wheres else "1=1"
    #
    #     # Simple SQL: Get all move lines for the accounts
    #     request = f"""
    #         SELECT
    #             id,
    #             account_id,
    #             debit,
    #             credit,
    #             analytic_distribution
    #         FROM {tables}
    #         WHERE account_id IN %s AND {filters}
    #     """
    #
    #     params = (tuple(accounts.ids),) + tuple(where_params)
    #
    #     _logger.info(f"Executing SQL query with {len(accounts)} accounts")
    #     _logger.info(f"SQL: {request}")
    #
    #     self.env.cr.execute(request, params)
    #     all_lines = self.env.cr.dictfetchall()
    #
    #     _logger.info(f"Total move lines found: {len(all_lines)}")
    #
    #     # Filter and calculate in Python
    #     account_result = {}
    #
    #     for line in all_lines:
    #         account_id = line['account_id']
    #         analytic_dist = line['analytic_distribution']
    #
    #         # Check if this line has any of our analytic accounts
    #         if not analytic_dist:
    #             _logger.debug(f"Line {line['id']}: No analytic distribution, skipping")
    #             continue
    #
    #         # Calculate percentage for our analytic accounts
    #         percentage = 0.0
    #         for analytic_id in analytic_ids:
    #             analytic_id_str = str(analytic_id)
    #             if analytic_id_str in analytic_dist:
    #                 percentage += float(analytic_dist[analytic_id_str])
    #                 _logger.debug(
    #                     f"Line {line['id']}: Found analytic {analytic_id_str} with {analytic_dist[analytic_id_str]}%")
    #
    #         if percentage == 0:
    #             continue
    #
    #         # Calculate proportional amounts
    #         proportional_debit = line['debit'] * (percentage / 100.0)
    #         proportional_credit = line['credit'] * (percentage / 100.0)
    #
    #         _logger.debug(f"Line {line['id']}: Debit {line['debit']} * {percentage}% = {proportional_debit}")
    #
    #         # Add to account totals
    #         if account_id not in account_result:
    #             account_result[account_id] = {'debit': 0.0, 'credit': 0.0, 'balance': 0.0}
    #
    #         account_result[account_id]['debit'] += proportional_debit
    #         account_result[account_id]['credit'] += proportional_credit
    #         account_result[account_id]['balance'] = account_result[account_id]['debit'] - account_result[account_id][
    #             'credit']
    #
    #     _logger.info(f"Accounts with filtered transactions: {len(account_result)}")
    #     for acc_id, values in account_result.items():
    #         _logger.info(
    #             f"  Account {acc_id}: Debit={values['debit']:.2f}, Credit={values['credit']:.2f}, Balance={values['balance']:.2f}")
    #
    #     # Build result list
    #     account_res = []
    #     for account in accounts:
    #         res = dict.fromkeys(['credit', 'debit', 'balance'], 0.0)
    #         currency = account.currency_id or self.env.company.currency_id
    #
    #         res.update({
    #             'code': account.code,
    #             'name': account.name,
    #         })
    #
    #         if account.id in account_result:
    #             res['debit'] = account_result[account.id]['debit']
    #             res['credit'] = account_result[account.id]['credit']
    #             res['balance'] = account_result[account.id]['balance']
    #
    #         # Apply display filter
    #         if display_account == 'all':
    #             account_res.append(res)
    #         elif display_account == 'not_zero' and not currency.is_zero(res['balance']):
    #             account_res.append(res)
    #         elif display_account == 'movement' and (
    #                 not currency.is_zero(res['debit']) or not currency.is_zero(res['credit'])
    #         ):
    #             account_res.append(res)
    #
    #     _logger.info(f"Accounts in final report: {len(account_res)}")
    #     _logger.info(f"=== END TRIAL BALANCE ANALYTIC FILTER ===")
    #
    #     return account_res

    def _get_accounts(self, accounts, display_account):
        """Override with simplified Python filtering approach."""

        # Get analytic filter from context
        analytic_account_ids = self.env.context.get('analytic_account_ids')

        # CRITICAL FIX: Use direct database query instead of parent method
        tables, where_clause, where_params = self.env['account.move.line']._query_get()
        tables = tables.replace('"', '') or 'account_move_line'

        wheres = []
        if where_clause.strip():
            wheres.append(where_clause.strip())
        filters = " AND ".join(wheres) if wheres else "1=1"

        # Get ALL move lines (without analytic filter first)
        request = f"""
            SELECT 
                account_id,
                SUM(debit) as debit,
                SUM(credit) as credit,
                analytic_distribution
            FROM {tables}
            WHERE account_id IN %s AND {filters}
            GROUP BY account_id, analytic_distribution
        """

        params = (tuple(accounts.ids),) + tuple(where_params)
        self.env.cr.execute(request, params)
        raw_results = self.env.cr.dictfetchall()

        # Now filter by analytic if needed (using your existing logic)
        if analytic_account_ids:
            # Use your existing filtering code here
            account_result = {}
            # ... (keep your existing analytic filtering logic)
        else:
            # NO FILTER: Build results directly from raw data
            account_result = {}
            for row in raw_results:
                acc_id = row['account_id']
                if acc_id not in account_result:
                    account_result[acc_id] = {'debit': 0.0, 'credit': 0.0, 'balance': 0.0}

                account_result[acc_id]['debit'] += row['debit'] or 0.0
                account_result[acc_id]['credit'] += row['credit'] or 0.0
                account_result[acc_id]['balance'] = (
                        account_result[acc_id]['debit'] - account_result[acc_id]['credit']
                )

        # Build final result list (keep your existing code)
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

        return account_res

    # ```
    #
    # ### Option 3: Check Balance Sheet Dependencies
    #
    # The
    # Balance
    # Sheet
    # might
    # be
    # using
    # the
    # same
    # broken
    # `accounting_pdf_reports`
    # module.
    #
    # ** Check
    # this: **
    # 1.
    # Go
    # to: ** Accounting → Configuration → Management → Financial
    # Reports **
    # 2.
    # Click
    # on ** "Balance Sheet" **
    # 3.
    # Check
    # which
    # module
    # provides
    # it
    # 4.
    # If
    # it
    # 's from `accounting_pdf_reports`, that'
    # s
    # your
    # problem
    #
    # ## 🎯 Recommended Action:
    #
    # ** I
    # recommend
    # Option
    # 1 ** as the
    # quickest
    # solution:
    #
    # 1. ** Keep
    # `custom_tb_report` ** ✅ (it works!)
    # 2. ** Uninstall
    # `account_trial_balance_warehouse` ** ❌ (it's broken)
    # 3. ** Check if `accounting_pdf_reports` is affecting Balance Sheet **
    # 4. If Balance Sheet is also from that module, consider replacing it with Odoo's standard Balance Sheet
    #
    # ** To verify: **
    # ```
    # Apps → Installed → Search "accounting_pdf_reports"
    # → Check what reports it provides
    # → Consider uninstalling if it's causing issues
    # @api.model
    def _get_report_values(self, docids, data=None):
        """Override to pass analytic accounts to context and display them in report."""
        # Get base report values from parent
        res = super()._get_report_values(docids, data=data)

        # Add analytic account names for display in report header
        if data and data.get('form', {}).get('analytic_account_ids'):
            analytic_ids = data['form']['analytic_account_ids']
            analytic_accounts = self.env['account.analytic.account'].browse(analytic_ids)
            res['analytic_accounts'] = [acc.name for acc in analytic_accounts]
            _logger.info(f"Report will show analytic accounts: {res['analytic_accounts']}")
        else:
            res['analytic_accounts'] = []

        return res
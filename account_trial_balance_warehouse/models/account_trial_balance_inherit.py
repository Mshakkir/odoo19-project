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

    def _get_accounts(self, accounts, display_account):
        """
        Override to add analytic account filtering using analytic_distribution.

        In Odoo 19, analytic accounts are stored in JSON field 'analytic_distribution'
        Format: {"account_id": percentage} e.g., {"2": 100.0, "3": 50.0}
        """
        # Get analytic filter from context
        analytic_account_ids = self.env.context.get('analytic_account_ids')

        if not analytic_account_ids:
            # No filter - use parent method (show all)
            return super()._get_accounts(accounts, display_account)

        # Extract IDs if it's a recordset
        if hasattr(analytic_account_ids, 'ids'):
            analytic_ids = analytic_account_ids.ids
        else:
            analytic_ids = analytic_account_ids

        _logger.info(f"=== TRIAL BALANCE ANALYTIC FILTER ACTIVE ===")
        _logger.info(f"Filtering by analytic account IDs: {analytic_ids}")

        account_result = {}

        # Build SQL query with analytic distribution filter
        tables, where_clause, where_params = self.env['account.move.line']._query_get()
        tables = tables.replace('"', '') or 'account_move_line'

        wheres = []
        if where_clause.strip():
            wheres.append(where_clause.strip())

        # Add analytic distribution filter using PostgreSQL JSON operators
        # Check if any of our analytic_ids exist in the JSON keys
        analytic_conditions = []
        for analytic_id in analytic_ids:
            analytic_conditions.append(f"analytic_distribution ? '{analytic_id}'")

        analytic_filter = "(" + " OR ".join(analytic_conditions) + ")"
        wheres.append(analytic_filter)

        filters = " AND ".join(wheres)

        # SQL query to get debit, credit, balance per account
        # We need to calculate proportional amounts based on analytic_distribution percentages
        request = f"""
            SELECT 
                account_id AS id,
                SUM(
                    CASE 
                        WHEN analytic_distribution IS NOT NULL THEN
                            debit * (
                                SELECT COALESCE(SUM((value::jsonb->>key)::numeric), 0)
                                FROM jsonb_each_text(analytic_distribution) 
                                WHERE key IN ({','.join(["'" + str(aid) + "'" for aid in analytic_ids])})
                            ) / 100.0
                        ELSE 0
                    END
                ) AS debit,
                SUM(
                    CASE 
                        WHEN analytic_distribution IS NOT NULL THEN
                            credit * (
                                SELECT COALESCE(SUM((value::jsonb->>key)::numeric), 0)
                                FROM jsonb_each_text(analytic_distribution) 
                                WHERE key IN ({','.join(["'" + str(aid) + "'" for aid in analytic_ids])})
                            ) / 100.0
                        ELSE 0
                    END
                ) AS credit
            FROM {tables}
            WHERE account_id IN %s AND {filters}
            GROUP BY account_id
        """

        params = (tuple(accounts.ids),) + tuple(where_params)

        _logger.info(f"Executing SQL query with {len(accounts)} accounts")
        self.env.cr.execute(request, params)

        for row in self.env.cr.dictfetchall():
            account_id = row.pop('id')
            row['balance'] = row['debit'] - row['credit']
            account_result[account_id] = row
            _logger.info(
                f"  Account {account_id}: Debit={row['debit']:.2f}, Credit={row['credit']:.2f}, Balance={row['balance']:.2f}")

        _logger.info(f"Total accounts with transactions: {len(account_result)}")

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
                res['debit'] = account_result[account.id].get('debit', 0.0)
                res['credit'] = account_result[account.id].get('credit', 0.0)
                res['balance'] = account_result[account.id].get('balance', 0.0)

            # Apply display filter
            if display_account == 'all':
                account_res.append(res)
            elif display_account == 'not_zero' and not currency.is_zero(res['balance']):
                account_res.append(res)
            elif display_account == 'movement' and (
                    not currency.is_zero(res['debit']) or not currency.is_zero(res['credit'])
            ):
                account_res.append(res)

        _logger.info(f"Accounts in final report: {len(account_res)}")
        _logger.info(f"=== END TRIAL BALANCE ANALYTIC FILTER ===")

        return account_res

    @api.model
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
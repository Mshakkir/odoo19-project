from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)


class AccountBalanceReport(models.TransientModel):
    """Extended Trial Balance wizard with analytic filter and detailed view."""

    _inherit = 'account.balance.report'

    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        'account_balance_analytic_account_rel',
        'report_id',
        'analytic_id',
        string='Analytic Accounts (Warehouses)',
        help='Filter Trial Balance by warehouse analytic accounts. '
             'Leave empty to show combined report for all warehouses.'
    )

    def _print_report(self, data):
        """Override to pass analytic filter to PDF report."""
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

    def open_trial_balance(self):
        """Open detailed trial balance view with analytic filtering."""
        self.ensure_one()

        # Clear previous TB lines for this wizard
        self.env['trial.balance.line'].search([('wizard_id', '=', self.id)]).unlink()

        # Get all accounts
        accounts = self.env['account.account'].search([])

        analytic_ids = self.analytic_account_ids.ids if self.analytic_account_ids else []

        _logger.info(f"=== OPENING TRIAL BALANCE DETAILS ===")
        _logger.info(f"Date range: {self.date_from} to {self.date_to}")
        _logger.info(f"Analytic filter: {analytic_ids}")

        for account in accounts:
            # Base domain for move lines
            domain = [
                ('account_id', '=', account.id),
                ('move_id.state', '=', 'posted'),
            ]

            # Get all move lines for this account
            all_move_lines = self.env['account.move.line'].search(domain)

            # Filter by analytic accounts if selected
            if analytic_ids:
                filtered_lines = self._filter_lines_by_analytic(all_move_lines, analytic_ids)
            else:
                filtered_lines = all_move_lines

            if not filtered_lines:
                continue

            # Calculate opening balance (before date_from)
            if self.date_from:
                opening_lines = filtered_lines.filtered(lambda l: l.date < self.date_from)
                opening = self._calculate_balance(opening_lines, analytic_ids)
            else:
                opening = 0.0

            # Calculate period movements (within date range)
            if self.date_from and self.date_to:
                period_lines = filtered_lines.filtered(
                    lambda l: self.date_from <= l.date <= self.date_to
                )
            else:
                period_lines = filtered_lines

            debit = self._calculate_debit(period_lines, analytic_ids)
            credit = self._calculate_credit(period_lines, analytic_ids)
            ending = opening + debit - credit

            # Only create line if there's activity or balance
            if opening != 0 or debit != 0 or credit != 0 or ending != 0:
                self.env['trial.balance.line'].create({
                    'wizard_id': self.id,
                    'account_id': account.id,
                    'opening_balance': opening,
                    'debit': debit,
                    'credit': credit,
                    'ending_balance': ending,
                    'move_line_ids': [(6, 0, period_lines.ids)],
                })

        _logger.info(f"=== TRIAL BALANCE DETAILS CREATED ===")

        return {
            'name': 'Trial Balance Details',
            'type': 'ir.actions.act_window',
            'res_model': 'trial.balance.line',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [('wizard_id', '=', self.id)],
            'context': {'default_wizard_id': self.id},
        }

    def _filter_lines_by_analytic(self, move_lines, analytic_ids):
        """Filter move lines that have the specified analytic accounts."""
        filtered = self.env['account.move.line']

        for line in move_lines:
            if not line.analytic_distribution:
                continue

            # Check if any of the selected analytic accounts are in this line
            line_analytic_ids = [int(k) for k in line.analytic_distribution.keys()]
            if any(acc_id in line_analytic_ids for acc_id in analytic_ids):
                filtered |= line

        return filtered

    def _calculate_balance(self, move_lines, analytic_ids):
        """Calculate balance considering analytic distribution."""
        balance = 0.0

        for line in move_lines:
            percentage = self._get_analytic_percentage(line, analytic_ids)
            balance += (line.debit - line.credit) * (percentage / 100.0)

        return balance

    def _calculate_debit(self, move_lines, analytic_ids):
        """Calculate debit considering analytic distribution."""
        debit = 0.0

        for line in move_lines:
            percentage = self._get_analytic_percentage(line, analytic_ids)
            debit += line.debit * (percentage / 100.0)

        return debit

    def _calculate_credit(self, move_lines, analytic_ids):
        """Calculate credit considering analytic distribution."""
        credit = 0.0

        for line in move_lines:
            percentage = self._get_analytic_percentage(line, analytic_ids)
            credit += line.credit * (percentage / 100.0)

        return credit

    def _get_analytic_percentage(self, move_line, analytic_ids):
        """Get the percentage allocation for selected analytic accounts."""
        if not analytic_ids:
            return 100.0

        if not move_line.analytic_distribution:
            return 0.0

        percentage = 0.0
        for analytic_id in analytic_ids:
            analytic_id_str = str(analytic_id)
            if analytic_id_str in move_line.analytic_distribution:
                percentage += float(move_line.analytic_distribution[analytic_id_str])

        return percentage


class ReportTrialBalance(models.AbstractModel):
    """Extend Trial Balance PDF report to filter by analytic accounts."""

    _inherit = 'report.accounting_pdf_reports.report_trialbalance'

    def _get_accounts(self, accounts, display_account):
        """Override to add analytic account filtering using analytic_distribution."""
        analytic_account_ids = self.env.context.get('analytic_account_ids')

        if not analytic_account_ids:
            _logger.info("No analytic filter - using parent method")
            return super()._get_accounts(accounts, display_account)

        # Extract IDs if it's a recordset
        if hasattr(analytic_account_ids, 'ids'):
            analytic_ids = analytic_account_ids.ids
        else:
            analytic_ids = list(analytic_account_ids) if isinstance(analytic_account_ids, (list, tuple)) else [
                analytic_account_ids]

        _logger.info(f"Filtering Trial Balance PDF by analytic accounts: {analytic_ids}")

        # Build SQL query to get all move lines
        tables, where_clause, where_params = self.env['account.move.line']._query_get()
        tables = tables.replace('"', '') or 'account_move_line'

        wheres = []
        if where_clause.strip():
            wheres.append(where_clause.strip())
        filters = " AND ".join(wheres) if wheres else "1=1"

        request = f"""
            SELECT 
                id,
                account_id,
                debit,
                credit,
                analytic_distribution
            FROM {tables}
            WHERE account_id IN %s AND {filters}
        """

        params = (tuple(accounts.ids),) + tuple(where_params)
        self.env.cr.execute(request, params)
        all_lines = self.env.cr.dictfetchall()

        _logger.info(f"Total move lines found: {len(all_lines)}")

        # Filter and calculate in Python
        account_result = {}

        for line in all_lines:
            account_id = line['account_id']
            analytic_dist = line['analytic_distribution']

            if not analytic_dist:
                continue

            # Calculate percentage for selected analytic accounts
            percentage = 0.0
            for analytic_id in analytic_ids:
                analytic_id_str = str(analytic_id)
                if analytic_id_str in analytic_dist:
                    percentage += float(analytic_dist[analytic_id_str])

            if percentage == 0:
                continue

            # Calculate proportional amounts
            proportional_debit = line['debit'] * (percentage / 100.0)
            proportional_credit = line['credit'] * (percentage / 100.0)

            # Add to account totals
            if account_id not in account_result:
                account_result[account_id] = {'debit': 0.0, 'credit': 0.0, 'balance': 0.0}

            account_result[account_id]['debit'] += proportional_debit
            account_result[account_id]['credit'] += proportional_credit
            account_result[account_id]['balance'] = account_result[account_id]['debit'] - account_result[account_id][
                'credit']

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
                    not currency.is_zero(res['debit']) or not currency.is_zero(res['credit'])):
                account_res.append(res)

        _logger.info(f"Accounts in PDF report: {len(account_res)}")
        return account_res

    @api.model
    def _get_report_values(self, docids, data=None):
        """Override to pass analytic accounts to context and display in report header."""
        res = super()._get_report_values(docids, data=data)

        if data and data.get('form', {}).get('analytic_account_ids'):
            analytic_ids = data['form']['analytic_account_ids']
            analytic_accounts = self.env['account.analytic.account'].browse(analytic_ids)
            res['analytic_accounts'] = [acc.name for acc in analytic_accounts]
        else:
            res['analytic_accounts'] = []

        return res
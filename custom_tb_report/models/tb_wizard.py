from odoo import models
import logging

_logger = logging.getLogger(__name__)


class AccountBalanceReportInherit(models.TransientModel):
    _inherit = 'account.balance.report'

    def _filter_lines_by_analytic(self, move_lines, analytic_ids):
        """
        Filter and calculate proportional amounts based on analytic_distribution.

        Args:
            move_lines: recordset of account.move.line
            analytic_ids: list of analytic account IDs to filter by

        Returns:
            dict: {debit: float, credit: float}
        """
        if not analytic_ids:
            # No filter - return full amounts
            return {
                'debit': sum(move_lines.mapped('debit')),
                'credit': sum(move_lines.mapped('credit'))
            }

        total_debit = 0.0
        total_credit = 0.0

        for line in move_lines:
            analytic_dist = line.analytic_distribution

            if not analytic_dist:
                continue

            # Calculate percentage for our analytic accounts
            percentage = 0.0
            for analytic_id in analytic_ids:
                analytic_id_str = str(analytic_id)
                if analytic_id_str in analytic_dist:
                    percentage += float(analytic_dist[analytic_id_str])

            if percentage == 0:
                continue

            # Calculate proportional amounts
            total_debit += line.debit * (percentage / 100.0)
            total_credit += line.credit * (percentage / 100.0)

        return {
            'debit': total_debit,
            'credit': total_credit
        }

    def open_trial_balance(self):
        self.ensure_one()

        # Clear previous TB lines
        self.env['trial.balance.line'].search([('wizard_id', '=', self.id)]).unlink()

        # Get analytic filter from the wizard
        analytic_ids = self.analytic_account_ids.ids if self.analytic_account_ids else []

        if analytic_ids:
            analytic_names = ', '.join(self.analytic_account_ids.mapped('name'))
            _logger.info(f"TB Lines: Filtering by analytic accounts {analytic_ids} - {analytic_names}")
            window_title = f'Trial Balance - {analytic_names}'
        else:
            _logger.info("TB Lines: No analytic filter - showing all warehouses (combined)")
            window_title = 'Trial Balance - All Warehouses (Combined)'

        accounts = self.env['account.account'].search([])

        for account in accounts:
            # Get all posted move lines for this account
            move_lines = self.env['account.move.line'].search([
                ('account_id', '=', account.id),
                ('move_id.state', '=', 'posted'),
            ])

            # Opening balance: sum of (debit - credit) before date_from
            if self.date_from:
                opening_lines = move_lines.filtered(lambda l: l.date < self.date_from)
            else:
                opening_lines = move_lines.browse([])

            # Calculate opening balance with analytic filter
            opening_data = self._filter_lines_by_analytic(opening_lines, analytic_ids)
            opening = opening_data['debit'] - opening_data['credit']

            # Lines within the period
            if self.date_from and self.date_to:
                period_lines = move_lines.filtered(lambda l: self.date_from <= l.date <= self.date_to)
            else:
                period_lines = move_lines

            # Calculate period amounts with analytic filter
            period_data = self._filter_lines_by_analytic(period_lines, analytic_ids)
            debit = period_data['debit']
            credit = period_data['credit']

            ending = opening + debit - credit

            # Only create line if there's any activity
            # Remove these 2 lines if you want to show all accounts even with zero balances
            if opening == 0 and debit == 0 and credit == 0 and ending == 0:
                continue

            # Create TB line
            self.env['trial.balance.line'].create({
                'wizard_id': self.id,
                'account_id': account.id,
                'opening_balance': opening,
                'debit': debit,
                'credit': credit,
                'ending_balance': ending,
            })

        return {
            'name': window_title,
            'type': 'ir.actions.act_window',
            'res_model': 'trial.balance.line',
            'views': [
                (self.env.ref('custom_tb_report.view_trial_balance_line_list').id, 'list'),
                (self.env.ref('custom_tb_report.view_trial_balance_line_form').id, 'form'),
            ],
            'target': 'current',
            'domain': [('wizard_id', '=', self.id)],
        }

# from odoo import models
# import logging
#
# _logger = logging.getLogger(__name__)
#
#
# class AccountBalanceReportInherit(models.TransientModel):
#     _inherit = 'account.balance.report'
#
#     def _filter_lines_by_analytic(self, move_lines, analytic_ids):
#         """
#         Filter and calculate proportional amounts based on analytic_distribution.
#
#         Args:
#             move_lines: recordset of account.move.line
#             analytic_ids: list of analytic account IDs to filter by
#
#         Returns:
#             dict: {debit: float, credit: float}
#         """
#         if not analytic_ids:
#             # No filter - return full amounts
#             return {
#                 'debit': sum(move_lines.mapped('debit')),
#                 'credit': sum(move_lines.mapped('credit'))
#             }
#
#         total_debit = 0.0
#         total_credit = 0.0
#
#         for line in move_lines:
#             analytic_dist = line.analytic_distribution
#
#             if not analytic_dist:
#                 continue
#
#             # Calculate percentage for our analytic accounts
#             percentage = 0.0
#             for analytic_id in analytic_ids:
#                 analytic_id_str = str(analytic_id)
#                 if analytic_id_str in analytic_dist:
#                     percentage += float(analytic_dist[analytic_id_str])
#
#             if percentage == 0:
#                 continue
#
#             # Calculate proportional amounts
#             total_debit += line.debit * (percentage / 100.0)
#             total_credit += line.credit * (percentage / 100.0)
#
#         return {
#             'debit': total_debit,
#             'credit': total_credit
#         }
#
#     def open_trial_balance(self):
#         self.ensure_one()
#
#         # Clear previous TB lines
#         self.env['trial.balance.line'].search([('wizard_id', '=', self.id)]).unlink()
#
#         # Get analytic filter from the wizard
#         analytic_ids = self.analytic_account_ids.ids if self.analytic_account_ids else []
#
#         if analytic_ids:
#             analytic_names = ', '.join(self.analytic_account_ids.mapped('name'))
#             _logger.info(f"TB Lines: Filtering by analytic accounts {analytic_ids} - {analytic_names}")
#             window_title = f'Trial Balance - {analytic_names}'
#         else:
#             _logger.info("TB Lines: No analytic filter - showing all warehouses (combined)")
#             window_title = 'Trial Balance - All Warehouses (Combined)'
#
#         accounts = self.env['account.account'].search([])
#
#         for account in accounts:
#             # Get all posted move lines for this account
#             move_lines = self.env['account.move.line'].search([
#                 ('account_id', '=', account.id),
#                 ('move_id.state', '=', 'posted'),
#             ])
#
#             # Opening balance: sum of (debit - credit) before date_from
#             if self.date_from:
#                 opening_lines = move_lines.filtered(lambda l: l.date < self.date_from)
#             else:
#                 opening_lines = move_lines.browse([])
#
#             # Calculate opening balance with analytic filter
#             opening_data = self._filter_lines_by_analytic(opening_lines, analytic_ids)
#             opening = opening_data['debit'] - opening_data['credit']
#
#             # Lines within the period
#             if self.date_from and self.date_to:
#                 period_lines = move_lines.filtered(lambda l: self.date_from <= l.date <= self.date_to)
#             else:
#                 period_lines = move_lines
#
#             # Calculate period amounts with analytic filter
#             period_data = self._filter_lines_by_analytic(period_lines, analytic_ids)
#             debit = period_data['debit']
#             credit = period_data['credit']
#
#             ending = opening + debit - credit
#
#             # Only create line if there's any activity
#             # Remove these 2 lines if you want to show all accounts even with zero balances
#             if opening == 0 and debit == 0 and credit == 0 and ending == 0:
#                 continue
#
#             # Create TB line
#             self.env['trial.balance.line'].create({
#                 'wizard_id': self.id,
#                 'account_id': account.id,
#                 'opening_balance': opening,
#                 'debit': debit,
#                 'credit': credit,
#                 'ending_balance': ending,
#                 'is_total': False,
#             })
#
#         # Calculate and create totals row
#         totals = self.env['trial.balance.line'].calculate_totals(self.id)
#
#         # Create a total row (with account_id as False for identification)
#         self.env['trial.balance.line'].create({
#             'wizard_id': self.id,
#             'account_id': False,
#             'opening_balance': totals['opening_debit'] - totals['opening_credit'],
#             'debit': totals['debit'],
#             'credit': totals['credit'],
#             'ending_balance': totals['ending_debit'] - totals['ending_credit'],
#             'is_total': True,
#         })
#
#         return {
#             'name': window_title,
#             'type': 'ir.actions.act_window',
#             'res_model': 'trial.balance.line',
#             'views': [
#                 (self.env.ref('custom_tb_report.view_trial_balance_line_list').id, 'list'),
#                 (self.env.ref('custom_tb_report.view_trial_balance_line_form').id, 'form'),
#             ],
#             'target': 'current',
#             'domain': [('wizard_id', '=', self.id)],
#         }
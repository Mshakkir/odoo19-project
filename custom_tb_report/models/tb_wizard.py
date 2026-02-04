#
#
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
#         accounts = self.env['account.account'].search([('code', '!=', 'TOTAL')])
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
#         # Get or create a dummy account for the total row display
#         total_account = self.env['account.account'].search([('code', '=', 'TOTAL')], limit=1)
#         if not total_account:
#             # Create a display-only account for totals
#             total_account = self.env['account.account'].create({
#                 'code': 'TOTAL',
#                 'name': 'TOTAL',
#                 'account_type': 'asset_current',
#                 'reconcile': False,
#             })
#
#         # Create a total row
#         self.env['trial.balance.line'].create({
#             'wizard_id': self.id,
#             'account_id': total_account.id,
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
#
#     def print_detailed_trial_balance(self):
#         """
#         Print detailed trial balance report with all transactions.
#         First ensures trial balance lines are created, then prints the report.
#         """
#         self.ensure_one()
#
#         # First, ensure trial balance lines exist
#         existing_lines = self.env['trial.balance.line'].search([('wizard_id', '=', self.id)])
#         if not existing_lines:
#             # Generate trial balance lines
#             self.open_trial_balance()
#
#         # Return report action
#         return self.env.ref('custom_tb_report.action_report_trial_balance_detailed').report_action(self)

from odoo import models
import logging
import base64
import io
from datetime import datetime

_logger = logging.getLogger(__name__)

try:
    import xlsxwriter
except ImportError:
    _logger.warning('xlsxwriter not installed. Excel export will not work.')


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

        accounts = self.env['account.account'].search([('code', '!=', 'TOTAL')])

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
                'is_total': False,
            })

        # Calculate and create totals row
        totals = self.env['trial.balance.line'].calculate_totals(self.id)

        # Get or create a dummy account for the total row display
        total_account = self.env['account.account'].search([('code', '=', 'TOTAL')], limit=1)
        if not total_account:
            # Create a display-only account for totals
            total_account = self.env['account.account'].create({
                'code': 'TOTAL',
                'name': 'TOTAL',
                'account_type': 'asset_current',
                'reconcile': False,
            })

        # Create a total row
        self.env['trial.balance.line'].create({
            'wizard_id': self.id,
            'account_id': total_account.id,
            'opening_balance': totals['opening_debit'] - totals['opening_credit'],
            'debit': totals['debit'],
            'credit': totals['credit'],
            'ending_balance': totals['ending_debit'] - totals['ending_credit'],
            'is_total': True,
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

    def print_detailed_trial_balance(self):
        """
        Print detailed trial balance report with all transactions.
        First ensures trial balance lines are created, then prints the report.
        """
        self.ensure_one()

        # First, ensure trial balance lines exist
        existing_lines = self.env['trial.balance.line'].search([('wizard_id', '=', self.id)])
        if not existing_lines:
            # Generate trial balance lines
            self.open_trial_balance()

        # Return report action
        return self.env.ref('custom_tb_report.action_report_trial_balance_detailed').report_action(self)

    def export_trial_balance_excel(self):
        """
        Export trial balance data to Excel file
        """
        self.ensure_one()

        # Ensure trial balance lines exist
        existing_lines = self.env['trial.balance.line'].search([('wizard_id', '=', self.id)])
        if not existing_lines:
            # Generate trial balance lines
            self.open_trial_balance()
            existing_lines = self.env['trial.balance.line'].search([('wizard_id', '=', self.id)])

        # Create Excel file in memory
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Trial Balance')

        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D3D3D3',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })

        total_format = workbook.add_format({
            'bold': True,
            'bg_color': '#FFFF00',
            'border': 1,
            'num_format': '#,##0.00'
        })

        number_format = workbook.add_format({
            'num_format': '#,##0.00',
            'border': 1
        })

        text_format = workbook.add_format({
            'border': 1
        })

        # Set column widths
        worksheet.set_column('A:A', 15)  # Account Code
        worksheet.set_column('B:B', 40)  # Account Name
        worksheet.set_column('C:F', 18)  # Number columns

        # Write title
        analytic_ids = self.analytic_account_ids.ids if self.analytic_account_ids else []
        if analytic_ids:
            analytic_names = ', '.join(self.analytic_account_ids.mapped('name'))
            title = f'Trial Balance - {analytic_names}'
        else:
            title = 'Trial Balance - All Warehouses (Combined)'

        worksheet.merge_range('A1:F1', title, workbook.add_format({
            'bold': True,
            'font_size': 14,
            'align': 'center',
            'valign': 'vcenter'
        }))

        # Write date range
        date_range = ''
        if self.date_from and self.date_to:
            date_range = f"From {self.date_from.strftime('%d/%m/%Y')} To {self.date_to.strftime('%d/%m/%Y')}"
        elif self.date_from:
            date_range = f"From {self.date_from.strftime('%d/%m/%Y')}"
        elif self.date_to:
            date_range = f"To {self.date_to.strftime('%d/%m/%Y')}"

        if date_range:
            worksheet.merge_range('A2:F2', date_range, workbook.add_format({
                'align': 'center',
                'valign': 'vcenter'
            }))
            row = 3
        else:
            row = 2

        # Write headers
        worksheet.write(row, 0, 'Account Code', header_format)
        worksheet.write(row, 1, 'Account Name', header_format)
        worksheet.write(row, 2, 'Opening Balance', header_format)
        worksheet.write(row, 3, 'Debit', header_format)
        worksheet.write(row, 4, 'Credit', header_format)
        worksheet.write(row, 5, 'Ending Balance', header_format)

        row += 1

        # Write data
        lines = existing_lines.filtered(lambda l: not l.is_total).sorted(key=lambda r: r.account_id.code)
        for line in lines:
            worksheet.write(row, 0, line.account_id.code or '', text_format)
            worksheet.write(row, 1, line.account_id.name or '', text_format)
            worksheet.write(row, 2, line.opening_balance, number_format)
            worksheet.write(row, 3, line.debit, number_format)
            worksheet.write(row, 4, line.credit, number_format)
            worksheet.write(row, 5, line.ending_balance, number_format)
            row += 1

        # Write totals
        total_line = existing_lines.filtered(lambda l: l.is_total)
        if total_line:
            worksheet.write(row, 0, 'TOTAL', total_format)
            worksheet.write(row, 1, '', total_format)
            worksheet.write(row, 2, total_line.opening_balance, total_format)
            worksheet.write(row, 3, total_line.debit, total_format)
            worksheet.write(row, 4, total_line.credit, total_format)
            worksheet.write(row, 5, total_line.ending_balance, total_format)

        workbook.close()
        output.seek(0)
        excel_data = output.read()
        output.close()

        # Generate filename
        filename = f'Trial_Balance_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'

        # Create attachment
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(excel_data),
            'store_fname': filename,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        # Return download action
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
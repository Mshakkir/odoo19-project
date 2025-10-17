from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class AccountBalanceReportInherit(models.TransientModel):
    _inherit = 'account.balance.report'

    # Add new field for "All Companies" option
    include_all_companies = fields.Boolean(
        string='All Companies',
        default=False,
        help='Include transactions from all companies'
    )

    def open_trial_balance(self):
        self.ensure_one()

        # Clear previous TB lines
        self.env['trial.balance.line'].search([('wizard_id', '=', self.id)]).unlink()

        # Determine which companies to include
        if self.include_all_companies:
            # Get all companies
            companies = self.env['res.company'].search([])
            company_ids = companies.ids
            _logger.info(f"Processing ALL companies: {[c.name for c in companies]}")
        else:
            # Use only the selected company from wizard
            company_ids = [self.company_id.id] if self.company_id else [self.env.company.id]
            company_name = self.env['res.company'].browse(company_ids[0]).name
            _logger.info(f"Processing single company: {company_name}")

        # Get all accounts (don't filter by company - accounts might be shared)
        accounts = self.env['account.account'].search([])

        for account in accounts:
            # Build domain for move lines
            domain = [
                ('account_id', '=', account.id),
                ('move_id.state', '=', 'posted'),
                ('company_id', 'in', company_ids),
            ]

            # Get all posted move lines for this account
            move_lines = self.env['account.move.line'].search(domain)

            # Skip if no move lines found
            if not move_lines:
                continue

            # DEBUG: Log move lines details for specific accounts
            if account.code in ['102011', '104041', '201002']:
                _logger.info(f"\n=== Account {account.code} - {account.name} ===")
                _logger.info(f"Total move lines found: {len(move_lines)}")

                # Group by company to see breakdown
                for company_id in company_ids:
                    comp_lines = move_lines.filtered(lambda l: l.company_id.id == company_id)
                    if comp_lines:
                        company_name = self.env['res.company'].browse(company_id).name
                        comp_debit = sum(comp_lines.mapped('debit'))
                        comp_credit = sum(comp_lines.mapped('credit'))
                        _logger.info(f"  Company: {company_name}")
                        _logger.info(f"    Lines: {len(comp_lines)}")
                        _logger.info(f"    Debit: {comp_debit}, Credit: {comp_credit}")

                        # Show individual lines
                        for line in comp_lines[:5]:  # Show first 5 lines
                            _logger.info(
                                f"      Move: {line.move_id.name}, Date: {line.date}, Dr: {line.debit}, Cr: {line.credit}")

            # Opening balance: sum of (debit - credit) before date_from
            if self.date_from:
                opening_lines = move_lines.filtered(lambda l: l.date < self.date_from)
                opening = sum(opening_lines.mapped('debit')) - sum(opening_lines.mapped('credit'))
            else:
                opening = 0.0

            # Lines within the period
            if self.date_from and self.date_to:
                period_lines = move_lines.filtered(lambda l: self.date_from <= l.date <= self.date_to)
            elif self.date_to:
                period_lines = move_lines.filtered(lambda l: l.date <= self.date_to)
            elif self.date_from:
                period_lines = move_lines.filtered(lambda l: l.date >= self.date_from)
            else:
                period_lines = move_lines

            debit = sum(period_lines.mapped('debit'))
            credit = sum(period_lines.mapped('credit'))
            ending = opening + debit - credit

            # Only create TB line if there's activity
            if opening != 0 or debit != 0 or credit != 0:
                self.env['trial.balance.line'].create({
                    'wizard_id': self.id,
                    'account_id': account.id,
                    'opening_balance': opening,
                    'debit': debit,
                    'credit': credit,
                    'ending_balance': ending,
                })

        # Build report title
        if self.include_all_companies:
            report_title = 'Trial Balance - All Companies'
        else:
            company_name = self.company_id.name if self.company_id else self.env.company.name
            report_title = f'Trial Balance - {company_name}'

        return {
            'name': report_title,
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
#
# class AccountBalanceReportInherit(models.TransientModel):
#     _inherit = 'account.balance.report'  # <- inherit Trial Balance wizard
#
#     def open_trial_balance(self):
#         self.ensure_one()
#
#         # Clear previous TB lines
#         self.env['trial.balance.line'].search([('wizard_id', '=', self.id)]).unlink()
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
#                 opening_lines = move_lines.browse([])  # no opening lines if no date_from
#             opening = sum(opening_lines.mapped(lambda l: l.debit - l.credit))
#
#             # Lines within the period
#             if self.date_from and self.date_to:
#                 period_lines = move_lines.filtered(lambda l: self.date_from <= l.date <= self.date_to)
#             else:
#                 period_lines = move_lines
#             debit = sum(period_lines.mapped('debit'))
#             credit = sum(period_lines.mapped('credit'))
#
#             ending = opening + debit - credit
#
#             # Create TB line
#             self.env['trial.balance.line'].create({
#                 'wizard_id': self.id,
#                 'account_id': account.id,
#                 'opening_balance': opening,
#                 'debit': debit,
#                 'credit': credit,
#                 'ending_balance': ending,
#             })
#
#         return {
#             'name': 'Trial Balance',
#             'type': 'ir.actions.act_window',
#             'res_model': 'trial.balance.line',
#             'views': [
#                 (self.env.ref('custom_tb_report.view_trial_balance_line_list').id, 'list'),
#                 (self.env.ref('custom_tb_report.view_trial_balance_line_form').id, 'form'),
#             ],
#             'target': 'current',
#             'domain': [('wizard_id', '=', self.id)],
#         }

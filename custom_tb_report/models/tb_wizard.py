from odoo import models, fields, api


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
        else:
            # Use only the selected company from wizard
            company_ids = [self.company_id.id] if self.company_id else [self.env.company.id]

        # Get all accounts (don't filter by company - accounts might be shared)
        accounts = self.env['account.account'].search([])

        for account in accounts:
            # Build domain for move lines
            domain = [
                ('account_id', '=', account.id),
                ('move_id.state', '=', 'posted'),
            ]

            # Add company filter
            if company_ids:
                domain.append(('company_id', 'in', company_ids))

            # Get all posted move lines for this account
            move_lines = self.env['account.move.line'].search(domain)

            # Skip if no move lines found
            if not move_lines:
                continue

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

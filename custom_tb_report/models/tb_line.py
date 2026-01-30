# from odoo import models, fields, api
#
#
# class TrialBalanceLine(models.TransientModel):
#     _name = 'trial.balance.line'
#     _description = 'Trial Balance Line'
#
#     wizard_id = fields.Many2one('account.balance.report', string='Wizard')
#     account_id = fields.Many2one('account.account', string='Account')
#     opening_balance = fields.Monetary(string='Opening Balance', currency_field='company_currency_id')
#     debit = fields.Monetary(string='Debit', currency_field='company_currency_id')
#     credit = fields.Monetary(string='Credit', currency_field='company_currency_id')
#     ending_balance = fields.Monetary(string='Ending Balance', currency_field='company_currency_id')
#     company_currency_id = fields.Many2one('res.currency', string='Currency',
#                                           default=lambda self: self.env.company.currency_id)
#     is_total = fields.Boolean(string='Is Total Row', default=False)
#
#     @api.model
#     def calculate_totals(self, wizard_id):
#         """Calculate totals for the trial balance"""
#         lines = self.search([('wizard_id', '=', wizard_id), ('is_total', '=', False)])
#
#         total_opening_debit = sum(line.opening_balance for line in lines if line.opening_balance > 0)
#         total_opening_credit = abs(sum(line.opening_balance for line in lines if line.opening_balance < 0))
#         total_debit = sum(lines.mapped('debit'))
#         total_credit = sum(lines.mapped('credit'))
#         total_ending_debit = sum(line.ending_balance for line in lines if line.ending_balance > 0)
#         total_ending_credit = abs(sum(line.ending_balance for line in lines if line.ending_balance < 0))
#
#         return {
#             'opening_debit': total_opening_debit,
#             'opening_credit': total_opening_credit,
#             'debit': total_debit,
#             'credit': total_credit,
#             'ending_debit': total_ending_debit,
#             'ending_credit': total_ending_credit,
#         }

from odoo import models, fields, api


class TrialBalanceLine(models.TransientModel):
    _name = 'trial.balance.line'
    _description = 'Trial Balance Line'

    wizard_id = fields.Many2one('account.balance.report', string='Wizard')
    account_id = fields.Many2one('account.account', string='Account')
    opening_balance = fields.Monetary(string='Opening Balance', currency_field='company_currency_id')
    debit = fields.Monetary(string='Debit', currency_field='company_currency_id')
    credit = fields.Monetary(string='Credit', currency_field='company_currency_id')
    ending_balance = fields.Monetary(string='Ending Balance', currency_field='company_currency_id')
    company_currency_id = fields.Many2one('res.currency', string='Currency',
                                          default=lambda self: self.env.company.currency_id)
    is_total = fields.Boolean(string='Is Total Row', default=False)

    @api.model
    def calculate_totals(self, wizard_id):
        """Calculate totals for the trial balance"""
        lines = self.search([('wizard_id', '=', wizard_id), ('is_total', '=', False)])

        total_opening_debit = sum(line.opening_balance for line in lines if line.opening_balance > 0)
        total_opening_credit = abs(sum(line.opening_balance for line in lines if line.opening_balance < 0))
        total_debit = sum(lines.mapped('debit'))
        total_credit = sum(lines.mapped('credit'))
        total_ending_debit = sum(line.ending_balance for line in lines if line.ending_balance > 0)
        total_ending_credit = abs(sum(line.ending_balance for line in lines if line.ending_balance < 0))

        return {
            'opening_debit': total_opening_debit,
            'opening_credit': total_opening_credit,
            'debit': total_debit,
            'credit': total_credit,
            'ending_debit': total_ending_debit,
            'ending_credit': total_ending_credit,
        }

    def action_view_partner_balances(self):
        """
        Open partner-wise breakdown showing each customer/vendor with their balances.
        This is the intermediate view before drilling to transactions.
        """
        self.ensure_one()

        # Skip if this is the total row
        if self.is_total:
            return {'type': 'ir.actions.act_window_close'}

        wizard = self.wizard_id
        account = self.account_id

        # Get analytic filter from wizard
        analytic_ids = wizard.analytic_account_ids.ids if wizard.analytic_account_ids else []

        # Clear any existing partner balance lines for this combination
        self.env['trial.balance.partner.line'].search([
            ('account_line_id', '=', self.id)
        ]).unlink()

        # Build domain for move lines
        domain = [
            ('account_id', '=', account.id),
            ('move_id.state', '=', 'posted'),
            ('partner_id', '!=', False),  # Only lines with partners
        ]

        # Get all move lines for this account
        move_lines = self.env['account.move.line'].search(domain)

        # Filter by analytic if needed
        if analytic_ids:
            filtered_lines = move_lines.browse([])
            for line in move_lines:
                if line.analytic_distribution:
                    for analytic_id in analytic_ids:
                        if str(analytic_id) in line.analytic_distribution:
                            filtered_lines |= line
                            break
            move_lines = filtered_lines

        # Group by partner and calculate balances
        partner_data = {}
        for line in move_lines:
            partner = line.partner_id
            if partner.id not in partner_data:
                partner_data[partner.id] = {
                    'partner': partner,
                    'opening_debit': 0.0,
                    'opening_credit': 0.0,
                    'debit': 0.0,
                    'credit': 0.0,
                }

            # Calculate opening balance (before date_from)
            if wizard.date_from and line.date < wizard.date_from:
                if line.debit > 0:
                    partner_data[partner.id]['opening_debit'] += line.debit
                if line.credit > 0:
                    partner_data[partner.id]['opening_credit'] += line.credit

            # Calculate period amounts (within date range)
            elif wizard.date_from and wizard.date_to:
                if wizard.date_from <= line.date <= wizard.date_to:
                    partner_data[partner.id]['debit'] += line.debit
                    partner_data[partner.id]['credit'] += line.credit
            else:
                # No date filter - include all in period
                partner_data[partner.id]['debit'] += line.debit
                partner_data[partner.id]['credit'] += line.credit

        # Create partner balance lines
        for partner_id, data in partner_data.items():
            opening_balance = data['opening_debit'] - data['opening_credit']
            ending_balance = opening_balance + data['debit'] - data['credit']

            # Only create if there's activity
            if opening_balance != 0 or data['debit'] != 0 or data['credit'] != 0:
                self.env['trial.balance.partner.line'].create({
                    'account_line_id': self.id,
                    'partner_id': partner_id,
                    'opening_balance': opening_balance,
                    'debit': data['debit'],
                    'credit': data['credit'],
                    'ending_balance': ending_balance,
                })

        # Determine title based on account type
        account_type = account.account_type
        if 'receivable' in account_type:
            window_title = f'Customer Balances - {account.display_name}'
        elif 'payable' in account_type:
            window_title = f'Vendor Balances - {account.display_name}'
        else:
            window_title = f'Partner Balances - {account.display_name}'

        return {
            'name': window_title,
            'type': 'ir.actions.act_window',
            'res_model': 'trial.balance.partner.line',
            'view_mode': 'list,form',
            'domain': [('account_line_id', '=', self.id)],
            'target': 'current',
            'context': {'create': False, 'edit': False, 'delete': False},
        }

    def action_view_move_lines(self):
        """
        Open detailed journal items for this account line.
        Shows all accounting entries.
        """
        self.ensure_one()

        if self.is_total:
            return {'type': 'ir.actions.act_window_close'}

        wizard = self.wizard_id
        account = self.account_id

        analytic_ids = wizard.analytic_account_ids.ids if wizard.analytic_account_ids else []

        domain = [
            ('account_id', '=', account.id),
            ('move_id.state', '=', 'posted'),
        ]

        if wizard.date_from and wizard.date_to:
            domain.extend([
                ('date', '>=', wizard.date_from),
                ('date', '<=', wizard.date_to)
            ])

        move_lines = self.env['account.move.line'].search(domain)

        if analytic_ids:
            filtered_lines = move_lines.browse([])
            for line in move_lines:
                if line.analytic_distribution:
                    for analytic_id in analytic_ids:
                        if str(analytic_id) in line.analytic_distribution:
                            filtered_lines |= line
                            break
            move_lines = filtered_lines

        return {
            'name': f'Journal Items - {account.display_name}',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'list,form',
            'domain': [('id', 'in', move_lines.ids)],
            'target': 'current',
        }


class TrialBalancePartnerLine(models.TransientModel):
    _name = 'trial.balance.partner.line'
    _description = 'Trial Balance Partner Line'
    _order = 'partner_id'

    account_line_id = fields.Many2one('trial.balance.line', string='Account Line', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Partner', required=True)
    opening_balance = fields.Monetary(string='Opening Balance', currency_field='company_currency_id')
    debit = fields.Monetary(string='Debit', currency_field='company_currency_id')
    credit = fields.Monetary(string='Credit', currency_field='company_currency_id')
    ending_balance = fields.Monetary(string='Ending Balance', currency_field='company_currency_id')
    company_currency_id = fields.Many2one('res.currency', string='Currency',
                                          default=lambda self: self.env.company.currency_id)

    def action_view_partner_move_lines(self):
        """
        Open journal items for this specific partner.
        This is the final drill-down showing actual transactions.
        """
        self.ensure_one()

        wizard = self.account_line_id.wizard_id
        account = self.account_line_id.account_id
        partner = self.partner_id

        analytic_ids = wizard.analytic_account_ids.ids if wizard.analytic_account_ids else []

        domain = [
            ('account_id', '=', account.id),
            ('partner_id', '=', partner.id),
            ('move_id.state', '=', 'posted'),
        ]

        if wizard.date_from and wizard.date_to:
            domain.extend([
                ('date', '>=', wizard.date_from),
                ('date', '<=', wizard.date_to)
            ])

        move_lines = self.env['account.move.line'].search(domain)

        if analytic_ids:
            filtered_lines = move_lines.browse([])
            for line in move_lines:
                if line.analytic_distribution:
                    for analytic_id in analytic_ids:
                        if str(analytic_id) in line.analytic_distribution:
                            filtered_lines |= line
                            break
            move_lines = filtered_lines

        return {
            'name': f'Transactions - {partner.name} ({account.code})',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'list,form',
            'domain': [('id', 'in', move_lines.ids)],
            'target': 'current',
            'context': {
                'search_default_group_by_move': 1,  # Group by journal entry
            }
        }
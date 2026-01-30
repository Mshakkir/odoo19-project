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

    def action_view_partners(self):
        """
        Open a list of partners (customers/vendors) related to this account.
        - For Accounts Receivable: show customers
        - For Accounts Payable: show vendors
        """
        self.ensure_one()

        # Skip if this is the total row
        if self.is_total:
            return {'type': 'ir.actions.act_window_close'}

        wizard = self.wizard_id
        account = self.account_id

        # Get analytic filter from wizard
        analytic_ids = wizard.analytic_account_ids.ids if wizard.analytic_account_ids else []

        # Build domain for move lines
        domain = [
            ('account_id', '=', account.id),
            ('move_id.state', '=', 'posted'),
        ]

        # Add date filter if exists
        if wizard.date_from and wizard.date_to:
            domain.extend([
                ('date', '>=', wizard.date_from),
                ('date', '<=', wizard.date_to)
            ])

        # Get all move lines for this account in the period
        move_lines = self.env['account.move.line'].search(domain)

        # Filter by analytic if needed
        if analytic_ids:
            filtered_lines = move_lines.browse([])
            for line in move_lines:
                if line.analytic_distribution:
                    # Check if any of our analytic accounts are in the distribution
                    for analytic_id in analytic_ids:
                        if str(analytic_id) in line.analytic_distribution:
                            filtered_lines |= line
                            break
            move_lines = filtered_lines

        # Get unique partners from the move lines
        partner_ids = move_lines.mapped('partner_id').ids

        # Determine account type and setup appropriate view
        account_type = account.account_type

        # Check if this is Accounts Receivable or Payable
        if 'receivable' in account_type:
            window_title = f'Customers - {account.display_name}'
            partner_domain = [('id', 'in', partner_ids), ('customer_rank', '>', 0)]
        elif 'payable' in account_type:
            window_title = f'Vendors - {account.display_name}'
            partner_domain = [('id', 'in', partner_ids), ('supplier_rank', '>', 0)]
        else:
            # For other account types, just show all partners
            window_title = f'Partners - {account.display_name}'
            partner_domain = [('id', 'in', partner_ids)]

        return {
            'name': window_title,
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'view_mode': 'tree,form',
            'domain': partner_domain,
            'context': {
                'default_customer_rank': 1 if 'receivable' in account_type else 0,
                'default_supplier_rank': 1 if 'payable' in account_type else 0,
            },
            'target': 'current',
        }

    def action_view_move_lines(self):
        """
        Open detailed journal items for this account line.
        This shows all the accounting entries that make up the balance.
        """
        self.ensure_one()

        # Skip if this is the total row
        if self.is_total:
            return {'type': 'ir.actions.act_window_close'}

        wizard = self.wizard_id
        account = self.account_id

        # Get analytic filter from wizard
        analytic_ids = wizard.analytic_account_ids.ids if wizard.analytic_account_ids else []

        # Build domain for move lines
        domain = [
            ('account_id', '=', account.id),
            ('move_id.state', '=', 'posted'),
        ]

        # Add date filter if exists
        if wizard.date_from and wizard.date_to:
            domain.extend([
                ('date', '>=', wizard.date_from),
                ('date', '<=', wizard.date_to)
            ])

        # Get all move lines for this account in the period
        move_lines = self.env['account.move.line'].search(domain)

        # Filter by analytic if needed
        if analytic_ids:
            filtered_lines = move_lines.browse([])
            for line in move_lines:
                if line.analytic_distribution:
                    # Check if any of our analytic accounts are in the distribution
                    for analytic_id in analytic_ids:
                        if str(analytic_id) in line.analytic_distribution:
                            filtered_lines |= line
                            break
            move_lines = filtered_lines

        return {
            'name': f'Journal Items - {account.display_name}',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', move_lines.ids)],
            'target': 'current',
        }
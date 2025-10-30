# -*- coding: utf-8 -*-
from odoo import models, fields


class CustomBalanceSheetLine(models.TransientModel):
    _name = 'custom.balance.sheet.line'
    _description = 'Custom Balance Sheet Line'
    _order = 'section_type, name'

    name = fields.Char(string='Account', required=True)
    account_type = fields.Char(string='Account Type', readonly=True)
    section_type = fields.Selection([
        ('asset', 'Assets'),
        ('liability', 'Liabilities'),
        ('equity', 'Equity'),
        ('profit_loss', 'Profit/Loss'),
    ], string='Section', readonly=True)

    debit = fields.Monetary(string='Debit', currency_field='currency_id', readonly=True)
    credit = fields.Monetary(string='Credit', currency_field='currency_id', readonly=True)
    balance = fields.Monetary(string='Balance', currency_field='currency_id', readonly=True)

    account_id = fields.Many2one('account.account', string='Account', readonly=True)

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        readonly=True,
    )

    def action_view_ledger(self):
        """Open ledger lines filtered by this account and warehouse analytics from context."""
        if not self.account_id:
            return False

        account = self.account_id

        # Get date filters from context
        date_from = self.env.context.get('date_from')
        date_to = self.env.context.get('date_to')
        warehouse_analytic_ids = self.env.context.get('warehouse_analytic_ids')

        domain = [
            ('account_id', '=', account.id),
            ('move_id.state', '=', 'posted')
        ]

        if date_from:
            domain.append(('date', '>=', date_from))
        if date_to:
            domain.append(('date', '<=', date_to))

        # ✅ Apply warehouse filter
        if warehouse_analytic_ids:
            domain.append(('analytic_account_id', 'in', warehouse_analytic_ids))

        # Build title with warehouse info
        title = f'Ledger: {account.display_name}'
        if warehouse_analytic_ids:
            warehouses = self.env['account.analytic.account'].browse(warehouse_analytic_ids)
            warehouse_names = ', '.join(warehouses.mapped('name'))
            title = f'Ledger: {account.display_name} [{warehouse_names}]'

        return {
            'name': title,
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'list,form',
            'domain': domain,
            'context': {'default_account_id': account.id},
            'target': 'current',
        }




# # -*- coding: utf-8 -*-
# from odoo import models, fields
#
# class CustomBalanceSheetLine(models.TransientModel):
#     _name = 'custom.balance.sheet.line'
#     _description = 'Custom Balance Sheet Line'
#     _order = 'section_type, name'
#
#     name = fields.Char(string='Account', required=True)
#     account_type = fields.Char(string='Account Type', readonly=True)
#     section_type = fields.Selection([
#         ('asset', 'Assets'),
#         ('liability', 'Liabilities'),
#         ('equity', 'Equity'),
#         ('profit_loss', 'Profit/Loss'),
#     ], string='Section', readonly=True)
#
#     debit = fields.Monetary(string='Debit', currency_field='currency_id', readonly=True)
#     credit = fields.Monetary(string='Credit', currency_field='currency_id', readonly=True)
#     balance = fields.Monetary(string='Balance', currency_field='currency_id', readonly=True)
#
#     account_id = fields.Many2one('account.account', string='Account', readonly=True)
#
#     currency_id = fields.Many2one(
#         'res.currency',
#         string='Currency',
#         default=lambda self: self.env.company.currency_id,
#         readonly=True,
#     )
#
#     def action_view_ledger(self):
#         """Open ledger lines filtered by this account."""
#         if not self.account_id:
#             return False
#         account = self.account_id
#         return {
#             'name': f'Ledger: {account.display_name}',
#             'type': 'ir.actions.act_window',
#             'res_model': 'account.move.line',
#             'view_mode': 'list,form',
#             'domain': [
#                 ('account_id', '=', account.id),
#                 ('move_id.state', '=', 'posted')
#             ],
#             'context': {'default_account_id': account.id},
#             'target': 'current',
#         }

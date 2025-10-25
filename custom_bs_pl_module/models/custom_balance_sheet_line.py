## -*- coding: utf-8 -*-
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
        """Open ledger lines filtered by this account and optional analytic in context."""
        if not self.account_id:
            return False
        account = self.account_id
        domain = [
            ('account_id', '=', account.id),
            ('move_id.state', '=', 'posted')
        ]
        # add date filters when present in wizard context
        date_from = self.env.context.get('date_from')
        date_to = self.env.context.get('date_to')
        analytic = self.env.context.get('analytic_account_id')
        if date_from:
            domain.append(('date', '>=', date_from))
        if date_to:
            domain.append(('date', '<=', date_to))
        if analytic:
            domain.append(('analytic_account_id', '=', analytic))

        return {
            'name': f'Ledger: {account.display_name}',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'list,form',
            'domain': domain,
            'context': {'default_account_id': account.id},
            'target': 'current',
        }










# # -*- coding: utf-8 -*-
# from odoo import models, fields, api
#
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
#         # No ensure_one() because record may be transient or gone
#         account = self.account_id  # store in variable to avoid reference loss
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

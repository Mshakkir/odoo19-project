# -*- coding: utf-8 -*-
from odoo import models, fields, api


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
        """Open ledger lines filtered by this account."""
        if not self.account_id:
            return False
        # No ensure_one() because record may be transient or gone
        account = self.account_id  # store in variable to avoid reference loss
        return {
            'name': f'Ledger: {account.display_name}',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'tree,form',
            'domain': [
                ('account_id', '=', account.id),
                ('move_id.state', '=', 'posted')
            ],
            'context': {'default_account_id': account.id},
            'target': 'current',
        }

        }

        # from odoo import models, fields, api
        #
        # class CustomBalanceSheetLine(models.TransientModel):
        #     _name = 'custom.balance.sheet.line'
        #     _description = 'Custom Balance Sheet Line'
        #     _order = 'account_type, name'
        #
        #     name = fields.Char(string='Account', required=True)
        #     account_type = fields.Char(string='Type', readonly=True)
        #     debit = fields.Monetary(string='Debit', currency_field='currency_id', readonly=True)
        #     credit = fields.Monetary(string='Credit', currency_field='currency_id', readonly=True)
        #     balance = fields.Monetary(string='Balance', currency_field='currency_id', readonly=True)
        #     account_id = fields.Many2one('account.account', string='Account', readonly=True)
        #
        #     currency_id = fields.Many2one(
        #         'res.currency',
        #         string='Currency',
        #         default=lambda self: self.env.company.currency_id,
        #         readonly=True,
        #     )
        #
        #     @api.model
        #     def default_get(self, fields):
        #         res = super().default_get(fields)
        #         return res
        #
        #     def action_view_ledger(self):
        #         self.ensure_one()
        #         if not self.account_id:
        #             return False
        #         return {
        #             'name': f'Ledger: {self.account_id.display_name}',
        #             'type': 'ir.actions.act_window',
        #             'res_model': 'account.move.line',
        #             'view_mode': 'list,form',
        #             'domain': [('account_id', '=', self.account_id.id)],
        #             'context': {'default_account_id': self.account_id.id},
        #             'target': 'current',
        #         }

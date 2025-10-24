from odoo import models, api

class CustomBalanceSheetLine(models.TransientModel):
    _name = 'custom.balance.sheet.line'
    _description = 'Custom Balance Sheet Line'
    _order = 'account_type, name'

    name = fields.Char(string='Account', required=True)
    account_type = fields.Char(string='Type', readonly=True)
    debit = fields.Monetary(string='Debit', currency_field='currency_id', readonly=True)
    credit = fields.Monetary(string='Credit', currency_field='currency_id', readonly=True)
    balance = fields.Monetary(string='Balance', currency_field='currency_id', readonly=True)
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        readonly=True,
    )

    @api.model
    def action_view_ledger(self):
        """Open general ledger view for this account"""
        self.ensure_one()
        account = self.env['account.account'].search([('name', '=', self.name)], limit=1)
        if not account:
            return

        return {
            'type': 'ir.actions.act_window',
            'name': f'Ledger: {account.name}',
            'res_model': 'account.move.line',
            'view_mode': 'tree,form',
            'domain': [('account_id', '=', account.id)],
            'context': {'default_account_id': account.id},
        }

from odoo import models, fields, api, _
from datetime import date

class CustomBalanceSheetLine(models.TransientModel):
    _name = "custom.balance.sheet.line"
    _description = "Custom Balance Sheet Line"
    _order = "account_type, name"

    name = fields.Char(string="Account")
    account_id = fields.Many2one('account.account', string="Account Ref")
    debit = fields.Monetary(string="Debit", currency_field='currency_id')
    credit = fields.Monetary(string="Credit", currency_field='currency_id')
    balance = fields.Monetary(string="Balance", currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    account_type = fields.Selection([
        ('asset', 'Asset'),
        ('liability', 'Liability'),
        ('equity', 'Equity')
    ], string="Type", required=True)

    # Section totals (optional display lines)
    is_total = fields.Boolean(string="Is Total Line", default=False)

    @api.model
    def generate_lines(self, date_from, date_to, target_moves):
        """
        Generate balance sheet lines between date_from and date_to.
        Includes only Asset, Liability, and Equity accounts.
        """
        self.search([]).unlink()  # Clear old records

        move_state = ['posted'] if target_moves == 'posted' else ['draft', 'posted']
        company_currency = self.env.company.currency_id

        # Map Odoo account types to Balance Sheet categories
        type_map = {
            'asset_current': 'asset',
            'asset_non_current': 'asset',
            'liability_current': 'liability',
            'liability_non_current': 'liability',
            'equity': 'equity',
        }

        # Fetch relevant accounts
        accounts = self.env['account.account'].search([
            ('account_type', 'in', list(type_map.keys()))
        ])

        totals = {'asset': 0.0, 'liability': 0.0, 'equity': 0.0}

        for acc in accounts:
            account_type = type_map.get(acc.account_type)
            domain = [
                ('account_id', '=', acc.id),
                ('date', '>=', date_from),
                ('date', '<=', date_to),
                ('move_id.state', 'in', move_state)
            ]

            move_lines = self.env['account.move.line'].search(domain)
            debit = sum(move_lines.mapped('debit'))
            credit = sum(move_lines.mapped('credit'))
            balance = debit - credit  # Assets = Debit - Credit (debit nature)

            # For liabilities/equity, flip the sign to show positive balances on credit side
            if account_type in ['liability', 'equity']:
                balance = credit - debit

            if debit or credit:
                self.create({
                    'name': acc.display_name,
                    'account_id': acc.id,
                    'debit': debit,
                    'credit': credit,
                    'balance': balance,
                    'account_type': account_type,
                    'currency_id': company_currency.id,
                })
                totals[account_type] += balance

        # Add section total lines
        for ttype, total in totals.items():
            self.create({
                'name': f"Total {ttype.capitalize()}",
                'debit': 0.0,
                'credit': 0.0,
                'balance': total,
                'account_type': ttype,
                'is_total': True,
                'currency_id': company_currency.id,
            })

        # Compute check difference (Assets - (Liabilities + Equity))
        diff = totals['asset'] - (totals['liability'] + totals['equity'])
        if abs(diff) > 0.0001:
            self.create({
                'name': _("⚠️ Difference (Should be 0)"),
                'balance': diff,
                'currency_id': company_currency.id,
                'account_type': 'asset',
                'is_total': True,
            })

    def action_view_ledger(self):
        """Open account move lines (ledger) for this account"""
        self.ensure_one()
        return {
            'name': _('Ledger Entries'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'tree,form',
            'domain': [('account_id', '=', self.account_id.id)],
            'context': {'create': False, 'default_account_id': self.account_id.id},
            'target': 'current',
        }

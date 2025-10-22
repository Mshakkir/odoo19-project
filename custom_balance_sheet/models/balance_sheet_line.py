# custom_balance_sheet/models/balance_sheet_line.py
from odoo import api, fields, models, _

class BalanceSheetLine(models.Model):
    _name = 'balance.sheet.line'
    _description = 'Balance Sheet Detail Line'
    _order = 'account_id'

    wizard_uuid = fields.Char(string="Wizard UUID", index=True)
    account_id = fields.Many2one('account.account', string='Account', required=True, ondelete='cascade')
    debit = fields.Monetary(string='Debit', currency_field='company_currency_id')
    credit = fields.Monetary(string='Credit', currency_field='company_currency_id')
    balance = fields.Monetary(string='Balance', currency_field='company_currency_id')
    company_id = fields.Many2one('res.company', string='Company', readonly=True,
                                 default=lambda self: self.env.company)
    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)

    def action_open_ledger(self):
        """
        Open account.move.line filtered by account, dates, and move state according to the wizard_uuid saved in the context.
        The wizard_uuid lets us retrieve the filter used by the wizard.
        """
        self.ensure_one()
        wizard_uuid = self.env.context.get('default_wizard_uuid') or self.wizard_uuid
        if not wizard_uuid:
            # fallback: open all move lines for this account
            domain = [('account_id', '=', self.account_id.id)]
        else:
            wizard = self.env['balance.sheet.wizard'].search([('wizard_uuid', '=', wizard_uuid)], limit=1)
            if wizard:
                domain = [('account_id', '=', self.account_id.id),
                          ('date', '>=', wizard.date_from),
                          ('date', '<=', wizard.date_to)]
                if wizard.move_scope == 'posted':
                    domain.append(('move_id.state', '=', 'posted'))
            else:
                domain = [('account_id', '=', self.account_id.id)]
        action = self.env.ref('account.action_move_line_report').read()[0]
        action.update({
            'domain': domain,
            'context': dict(self.env.context, default_account_id=self.account_id.id),
        })
        return action

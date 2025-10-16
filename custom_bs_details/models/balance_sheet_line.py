# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class BalanceSheetLine(models.TransientModel):
    _name = 'balance.sheet.line'
    _description = 'Balance Sheet Line'
    name = fields.Char(string="Name")
    balance = fields.Monetary(string="Balance", currency_field='currency_id')

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
    )
    wizard_id = fields.Many2one('accounting.report', string='Wizard', ondelete='cascade')
    account_id = fields.Many2one('account.account', string='Account', required=True)
    debit = fields.Monetary(string='Debit', currency_field='company_currency_id', digits=(16,2))
    credit = fields.Monetary(string='Credit', currency_field='company_currency_id', digits=(16,2))
    balance = fields.Monetary(string='Balance', compute='_compute_balance', store=False, digits=(16,2))
    company_currency_id = fields.Many2one('res.currency', string='Currency', readonly=True, default=lambda self: self.env.company.currency_id.id)

    @api.depends('debit', 'credit')
    def _compute_balance(self):
        for rec in self:
            rec.balance = (rec.debit or 0.0) - (rec.credit or 0.0)

    def action_view_ledger(self):
        """Open journal items (account.move.line) for this account using the wizard's filters"""
        self.ensure_one()
        wizard = self.wizard_id
        if not wizard:
            raise UserError(_('Wizard context lost.'))

        domain = [('account_id', '=', self.account_id.id)]
        if getattr(wizard, 'date_from', False):
            domain.append(('date', '>=', wizard.date_from))
        if getattr(wizard, 'date_to', False):
            domain.append(('date', '<=', wizard.date_to))
        if getattr(wizard, 'journal_ids', False) and wizard.journal_ids:
            domain.append(('journal_id', 'in', wizard.journal_ids.ids))
        if getattr(wizard, 'target_move', False) and wizard.target_move == 'posted':
            domain.append(('move_id.state', '=', 'posted'))

        return {
            'name': _('Ledger Entries: %s') % (self.account_id.display_name),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'tree,form',
            'domain': domain,
            'target': 'current',
        }

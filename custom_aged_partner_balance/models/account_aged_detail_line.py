# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountAgedDetailLine(models.TransientModel):
    _name = 'account.aged.detail.line'
    _description = 'Aged Balance Detail Line'
    _order = 'total desc, partner_name'

    partner_id = fields.Many2one('res.partner', string='Partner', required=True)
    partner_name = fields.Char(string='Partner Name', required=True)
    trust = fields.Selection([
        ('good', 'Good Debtor'),
        ('normal', 'Normal Debtor'),
        ('bad', 'Bad Debtor')
    ], string='Trust', readonly=True)
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone')
    vat = fields.Char(string='Tax ID')

    not_due = fields.Monetary(string='Not Due', currency_field='currency_id')
    period_0 = fields.Monetary(string='0-30', currency_field='currency_id')
    period_1 = fields.Monetary(string='30-60', currency_field='currency_id')
    period_2 = fields.Monetary(string='60-90', currency_field='currency_id')
    period_3 = fields.Monetary(string='90-120', currency_field='currency_id')
    period_4 = fields.Monetary(string='120+', currency_field='currency_id')
    total = fields.Monetary(string='Total', currency_field='currency_id')

    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)

    # Store wizard configuration for drill-down
    wizard_id = fields.Many2one('account.aged.trial.balance', string='Wizard Reference')
    date_from = fields.Date(string='As of Date')
    period_length = fields.Integer(string='Period Length')

    def action_view_partner_ledger(self):
        """Open partner ledger for this specific partner"""
        self.ensure_one()

        action = self.env.ref('account.action_account_moves_all_a').read()[0]
        action['domain'] = [
            ('partner_id', '=', self.partner_id.id),
            ('date', '<=', self.date_from),
            ('parent_state', '!=', 'cancel'),
        ]

        if self.wizard_id:
            if self.wizard_id.result_selection == 'customer':
                action['domain'].append(('account_id.account_type', '=', 'asset_receivable'))
            elif self.wizard_id.result_selection == 'supplier':
                action['domain'].append(('account_id.account_type', '=', 'liability_payable'))

            if self.wizard_id.target_move == 'posted':
                action['domain'].append(('parent_state', '=', 'posted'))

        action['context'] = {
            'search_default_partner_id': self.partner_id.id,
            'default_partner_id': self.partner_id.id,
        }
        action['display_name'] = _('Partner Ledger: %s') % self.partner_name

        return action
# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class PartnerLedgerDetailLine(models.TransientModel):
    _name = 'partner.ledger.detail.line'
    _description = 'Partner Ledger Detail Line'
    _order = 'date, move_name'

    wizard_id = fields.Many2one(
        'account.report.partner.ledger',
        string='Wizard',
        ondelete='cascade'
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        readonly=True
    )

    partner_name = fields.Char(
        string='Partner Name',
        readonly=True
    )

    date = fields.Date(
        string='Date',
        readonly=True
    )

    move_id = fields.Many2one(
        'account.move',
        string='Journal Entry',
        readonly=True
    )

    move_name = fields.Char(
        string='Entry',
        readonly=True
    )

    journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        readonly=True
    )

    journal_code = fields.Char(
        string='Journal Code',
        readonly=True
    )

    account_id = fields.Many2one(
        'account.account',
        string='Account',
        readonly=True
    )

    account_name = fields.Char(
        string='Account Name',
        readonly=True
    )

    account_code = fields.Char(
        string='Account Code',
        readonly=True
    )

    ref = fields.Char(
        string='Reference',
        readonly=True
    )

    name = fields.Char(
        string='Label',
        readonly=True
    )

    debit = fields.Monetary(
        string='Debit',
        readonly=True,
        currency_field='currency_id'
    )

    credit = fields.Monetary(
        string='Credit',
        readonly=True,
        currency_field='currency_id'
    )

    balance = fields.Monetary(
        string='Balance',
        readonly=True,
        currency_field='currency_id'
    )

    amount_currency = fields.Monetary(
        string='Amount Currency',
        readonly=True,
        currency_field='foreign_currency_id'
    )

    foreign_currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        readonly=True
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Company Currency',
        default=lambda self: self.env.company.currency_id,
        readonly=True
    )

    reconciled = fields.Boolean(
        string='Reconciled',
        readonly=True
    )

    full_reconcile_id = fields.Many2one(
        'account.full.reconcile',
        string='Reconciliation',
        readonly=True
    )

    def action_view_move(self):
        """Open the related journal entry"""
        self.ensure_one()
        return {
            'name': _('Journal Entry'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.move_id.id,
            'target': 'current',
        }
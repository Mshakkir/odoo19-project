# -*- coding: utf-8 -*-
from odoo import fields, models, api, _


class AccountPartnerLedgerCustom(models.TransientModel):
    _inherit = "account.report.partner.ledger"

    show_details = fields.Boolean(
        string='Show Transaction Details',
        default=True,
        help="Show detailed transaction lines in the report"
    )

    def _get_report_data(self, data):
        """Override to add show_details to report data"""
        data = super(AccountPartnerLedgerCustom, self)._get_report_data(data)
        data['form'].update({
            'show_details': self.show_details,
        })
        return data

    def button_show_details(self):
        """
        Show detailed partner ledger lines in a list view.
        Similar to aged partner balance show_details functionality.
        """
        self.ensure_one()

        # Get the report data
        report_lines = self._get_ledger_detail_data()

        # Clear existing detail lines
        self.env['partner.ledger.detail.line'].search([]).unlink()

        # Create detail lines
        DetailLine = self.env['partner.ledger.detail.line']
        detail_ids = []

        for line_data in report_lines:
            vals = {
                'wizard_id': self.id,
                'partner_id': line_data.get('partner_id'),
                'partner_name': line_data.get('partner_name'),
                'date': line_data.get('date'),
                'move_id': line_data.get('move_id'),
                'move_name': line_data.get('move_name'),
                'journal_id': line_data.get('journal_id'),
                'journal_code': line_data.get('journal_code'),
                'account_id': line_data.get('account_id'),
                'account_name': line_data.get('account_name'),
                'account_code': line_data.get('account_code'),
                'ref': line_data.get('ref'),
                'name': line_data.get('name'),
                'debit': line_data.get('debit', 0.0),
                'credit': line_data.get('credit', 0.0),
                'balance': line_data.get('balance', 0.0),
                'amount_currency': line_data.get('amount_currency', 0.0),
                'foreign_currency_id': line_data.get('currency_id'),
                'reconciled': line_data.get('reconciled', False),
                'full_reconcile_id': line_data.get('full_reconcile_id'),
            }
            detail_line = DetailLine.create(vals)
            detail_ids.append(detail_line.id)

        # Determine title based on result_selection
        if self.result_selection == 'customer':
            action_name = _('Customer Ledger Details')
            partner_label = 'Customers'
        elif self.result_selection == 'supplier':
            action_name = _('Vendor Ledger Details')
            partner_label = 'Vendors'
        else:
            action_name = _('Partner Ledger Details')
            partner_label = 'Partners'

        # Build action title with date range
        date_from = self.date_from or 'Beginning'
        date_to = self.date_to or 'Today'
        action_title = f"{action_name} ({date_from} to {date_to}) - {len(detail_ids)} Transactions"

        return {
            'name': action_title,
            'type': 'ir.actions.act_window',
            'res_model': 'partner.ledger.detail.line',
            'view_mode': 'list,form',
            'domain': [('id', 'in', detail_ids)],
            'target': 'current',
            'context': {
                'create': False,
                'edit': False,
                'delete': False,
            },
        }

    def _get_ledger_detail_data(self):
        """
        Get all partner ledger transaction lines based on wizard filters.
        """
        self.ensure_one()

        # Build domain based on wizard filters
        domain = []

        # Account types based on result_selection
        if self.result_selection == 'customer':
            domain.append(('account_id.account_type', '=', 'asset_receivable'))
        elif self.result_selection == 'supplier':
            domain.append(('account_id.account_type', '=', 'liability_payable'))
        else:
            domain.append(('account_id.account_type', 'in', ['asset_receivable', 'liability_payable']))

        # Date filters
        if self.date_from:
            domain.append(('date', '>=', self.date_from))
        if self.date_to:
            domain.append(('date', '<=', self.date_to))

        # Partner filter
        if self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))
        else:
            domain.append(('partner_id', '!=', False))

        # Journal filter
        if self.journal_ids:
            domain.append(('journal_id', 'in', self.journal_ids.ids))

        # Target move filter
        if self.target_move == 'posted':
            domain.append(('parent_state', '=', 'posted'))

        # Reconciled filter
        if not self.reconciled:
            domain.append(('full_reconcile_id', '=', False))

        # Search move lines
        move_lines = self.env['account.move.line'].search(domain, order='partner_id, date, id')

        # Build result data
        result_lines = []
        running_balance = {}

        for line in move_lines:
            partner_id = line.partner_id.id

            # Initialize balance for partner
            if partner_id not in running_balance:
                running_balance[partner_id] = 0.0

            # Calculate balance
            running_balance[partner_id] += line.debit - line.credit

            result_lines.append({
                'partner_id': partner_id,
                'partner_name': line.partner_id.name,
                'date': line.date,
                'move_id': line.move_id.id,
                'move_name': line.move_id.name,
                'journal_id': line.journal_id.id,
                'journal_code': line.journal_id.code,
                'account_id': line.account_id.id,
                'account_name': line.account_id.name,
                'account_code': line.account_id.code,
                'ref': line.ref or line.move_id.ref or '',
                'name': line.name or '',
                'debit': line.debit,
                'credit': line.credit,
                'balance': running_balance[partner_id],
                'amount_currency': line.amount_currency if line.currency_id != line.company_currency_id else 0.0,
                'currency_id': line.currency_id.id if line.currency_id != line.company_currency_id else False,
                'reconciled': bool(line.full_reconcile_id),
                'full_reconcile_id': line.full_reconcile_id.id if line.full_reconcile_id else False,
            })

        return result_lines
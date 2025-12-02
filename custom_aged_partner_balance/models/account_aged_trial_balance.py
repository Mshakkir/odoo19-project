# -*- coding: utf-8 -*-

import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountAgedTrialBalance(models.TransientModel):
    _inherit = 'account.aged.trial.balance'

    partner_ids = fields.Many2many(
        'res.partner',
        string='Partners',
        help='Leave empty to include all partners'
    )

    def show_details(self):
        """
        Generate and display detailed aged balance lines for each partner
        """
        self.ensure_one()

        # Clear existing detail lines for this wizard
        self.env['account.aged.detail.line'].search([
            ('wizard_id', '=', self.id)
        ]).unlink()

        # Get report data
        data = self._get_report_data_for_details()
        partner_lines = self._get_partner_aging_data(data)

        # Create detail line records
        detail_lines = []
        for partner_data in partner_lines:
            vals = {
                'wizard_id': self.id,
                'partner_id': partner_data['partner_id'],
                'partner_name': partner_data['name'],
                'trust': partner_data.get('trust', 'normal'),
                'email': partner_data.get('email', ''),
                'phone': partner_data.get('phone', ''),
                'vat': partner_data.get('vat', ''),
                'not_due': partner_data.get('direction', 0.0),
                'period_0': partner_data.get('0', 0.0),
                'period_1': partner_data.get('1', 0.0),
                'period_2': partner_data.get('2', 0.0),
                'period_3': partner_data.get('3', 0.0),
                'period_4': partner_data.get('4', 0.0),
                'total': partner_data.get('total', 0.0),
                'date_from': self.date_from,
                'period_length': self.period_length,
                'company_id': self.company_id.id,
                'currency_id': self.company_id.currency_id.id,
            }
            detail_lines.append((0, 0, vals))

        # If no data found
        if not detail_lines:
            raise UserError(_('No data found for the selected criteria.'))

        # Create detail lines
        for cmd in detail_lines:
            self.env['account.aged.detail.line'].create(cmd[2])

        # Return action to show tree view
        action = {
            'name': _('Aged Balance Details'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.aged.detail.line',
            'view_mode': 'tree,form',
            'domain': [('wizard_id', '=', self.id)],
            'context': {
                'default_wizard_id': self.id,
                'search_default_group_by_partner': 0,
            },
            'target': 'current',
        }

        return action

    def _get_report_data_for_details(self):
        """Prepare report data structure"""
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': self.read([
                'date_from',
                'period_length',
                'result_selection',
                'target_move',
                'journal_ids',
                'partner_ids',
                'company_id'
            ])[0]
        }

        # Add period calculations
        period_length = self.period_length
        start = self.date_from

        for i in range(5)[::-1]:
            stop = start - relativedelta(days=period_length - 1)
            data['form'][str(i)] = {
                'name': (i != 0 and (str((5 - (i + 1)) * period_length) + '-' +
                                     str((5 - i) * period_length)) or ('+' + str(4 * period_length))),
                'stop': start.strftime('%Y-%m-%d'),
                'start': (i != 0 and stop.strftime('%Y-%m-%d') or False),
            }
            start = stop - relativedelta(days=1)

        return data

    def _get_partner_aging_data(self, data):
        """
        Calculate aging data for each partner
        This replicates the logic from the report parser
        """
        MoveLine = self.env['account.move.line']
        Partner = self.env['res.partner']

        # Build domain
        domain = [
            ('date', '<=', self.date_from),
            ('company_id', '=', self.company_id.id),
        ]

        if self.journal_ids:
            domain.append(('journal_id', 'in', self.journal_ids.ids))

        if self.result_selection == 'customer':
            domain.append(('account_id.account_type', '=', 'asset_receivable'))
        elif self.result_selection == 'supplier':
            domain.append(('account_id.account_type', '=', 'liability_payable'))
        else:
            domain.append(('account_id.account_type', 'in',
                           ['asset_receivable', 'liability_payable']))

        if self.target_move == 'posted':
            domain.append(('parent_state', '=', 'posted'))
        else:
            domain.append(('parent_state', '!=', 'cancel'))

        if self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))

        # Get move lines
        move_lines = MoveLine.search(domain)

        # Group by partner
        partner_data = {}
        for line in move_lines:
            partner_id = line.partner_id.id if line.partner_id else False
            if not partner_id:
                continue

            if partner_id not in partner_data:
                partner_data[partner_id] = {
                    'partner_id': partner_id,
                    'name': line.partner_id.name,
                    'trust': line.partner_id.trust,
                    'email': line.partner_id.email or '',
                    'phone': line.partner_id.phone or '',
                    'vat': line.partner_id.vat or '',
                    'direction': 0.0,  # Not due
                    '0': 0.0,
                    '1': 0.0,
                    '2': 0.0,
                    '3': 0.0,
                    '4': 0.0,
                    'total': 0.0,
                }

            # Calculate aging
            amount = line.debit - line.credit
            due_date = line.date_maturity or line.date

            # Determine which period this belongs to
            days_due = (self.date_from - due_date).days

            if days_due < 0:
                # Not yet due
                partner_data[partner_id]['direction'] += amount
            elif days_due < self.period_length:
                partner_data[partner_id]['0'] += amount
            elif days_due < self.period_length * 2:
                partner_data[partner_id]['1'] += amount
            elif days_due < self.period_length * 3:
                partner_data[partner_id]['2'] += amount
            elif days_due < self.period_length * 4:
                partner_data[partner_id]['3'] += amount
            else:
                partner_data[partner_id]['4'] += amount

            partner_data[partner_id]['total'] += amount

        # Convert to list and filter out zero balances
        result = []
        for p_id, p_data in partner_data.items():
            if abs(p_data['total']) > 0.01:  # Filter out near-zero balances
                result.append(p_data)

        # Sort by total descending
        result.sort(key=lambda x: abs(x['total']), reverse=True)

        return result
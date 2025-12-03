# models/aged_partner_inherit.py

import time
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountAgedTrialBalance(models.TransientModel):
    _inherit = 'account.aged.trial.balance'

    def show_details(self):
        """
        Override show_details to display detailed aged balance breakdown.
        Creates transient records for each partner with aging details.
        """
        self.ensure_one()

        # Get report data with periods
        data = {'form': self.read()[0]}
        data = self._get_report_data(data)

        # Get the aged partner balance report object
        ReportObj = self.env['report.accounting_pdf_reports.report_agedpartnerbalance']

        # Get partner lines with aging breakdown
        partner_lines = ReportObj._get_partner_lines(data['form'])

        # Clear existing detail lines for this wizard
        self.env['account.aged.detail.line'].search([]).unlink()

        # Create detail lines
        DetailLine = self.env['account.aged.detail.line']
        detail_ids = []

        for partner_data in partner_lines:
            vals = {
                'partner_id': partner_data.get('partner_id'),
                'partner_name': partner_data.get('name'),
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
                'wizard_id': self.id,
            }
            detail_line = DetailLine.create(vals)
            detail_ids.append(detail_line.id)

        # Determine action name based on report type
        if self.result_selection == 'customer':
            action_name = _('Aged Receivable Details')
        elif self.result_selection == 'supplier':
            action_name = _('Aged Payable Details')
        else:
            action_name = _('Aged Partner Balance Details')

        # Return action to display detail lines
        return {
            'name': action_name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.aged.detail.line',
            'view_mode': 'list,form',
            'views': [
                (self.env.ref('accounting_pdf_reports.view_aged_detail_tree').id, 'list'),
                (self.env.ref('accounting_pdf_reports.view_aged_detail_form').id, 'form')
            ],
            'domain': [('id', 'in', detail_ids)],
            'target': 'current',
            'context': {
                'default_wizard_id': self.id,
            },
        }


class AccountAgedDetailLine(models.TransientModel):
    _name = 'account.aged.detail.line'
    _description = 'Aged Balance Detail Line'
    _order = 'total desc, partner_name'

    wizard_id = fields.Many2one('account.aged.trial.balance', string='Wizard', ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
    partner_name = fields.Char(string='Partner Name', readonly=True)
    trust = fields.Selection([
        ('good', 'Good Debtor'),
        ('normal', 'Normal Debtor'),
        ('bad', 'Bad Debtor')
    ], string='Trust', readonly=True, default='normal')
    email = fields.Char(string='Email', readonly=True)
    phone = fields.Char(string='Phone', readonly=True)
    vat = fields.Char(string='Tax ID', readonly=True)

    not_due = fields.Monetary(string='Not Due', readonly=True, currency_field='currency_id')
    period_0 = fields.Monetary(string='0-30', readonly=True, currency_field='currency_id')
    period_1 = fields.Monetary(string='31-60', readonly=True, currency_field='currency_id')
    period_2 = fields.Monetary(string='61-90', readonly=True, currency_field='currency_id')
    period_3 = fields.Monetary(string='91-120', readonly=True, currency_field='currency_id')
    period_4 = fields.Monetary(string='120+', readonly=True, currency_field='currency_id')
    total = fields.Monetary(string='Total', readonly=True, currency_field='currency_id')

    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)

    def action_view_partner_ledger(self):
        """
        Open the partner ledger for the selected partner.
        """
        self.ensure_one()

        if not self.partner_id:
            raise UserError(_('No partner selected.'))

        # Get wizard data for date filtering
        wizard = self.wizard_id

        domain = [
            ('partner_id', '=', self.partner_id.id),
            ('date', '<=', wizard.date_from),
            ('reconciled', '=', False),
        ]

        # Filter by account type based on wizard selection
        if wizard.result_selection == 'customer':
            domain.append(('account_id.account_type', '=', 'asset_receivable'))
        elif wizard.result_selection == 'supplier':
            domain.append(('account_id.account_type', '=', 'liability_payable'))
        else:
            domain.append(('account_id.account_type', 'in', ['asset_receivable', 'liability_payable']))

        # Filter by posted moves if specified
        if wizard.target_move == 'posted':
            domain.append(('parent_state', '=', 'posted'))

        # Filter by journals
        if wizard.journal_ids:
            domain.append(('journal_id', 'in', wizard.journal_ids.ids))

        return {
            'name': _('Partner Ledger: %s') % self.partner_name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],
            'domain': domain,
            'target': 'current',
            'context': {
                'search_default_partner_id': self.partner_id.id,
                'default_partner_id': self.partner_id.id,
            },
        }
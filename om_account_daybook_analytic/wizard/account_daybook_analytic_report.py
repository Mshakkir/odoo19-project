from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import date


class AccountDayBookAnalyticReport(models.TransientModel):
    _name = "account.daybook.analytic.report"
    _description = "Day Book Report with Analytic Accounts"

    date_from = fields.Date(
        string='Start Date',
        default=date.today(),
        required=True
    )
    date_to = fields.Date(
        string='End Date',
        default=date.today(),
        required=True
    )
    target_move = fields.Selection(
        [('posted', 'Posted Entries'), ('all', 'All Entries')],
        string='Target Moves',
        required=True,
        default='posted'
    )
    journal_ids = fields.Many2many(
        'account.journal',
        string='Journals',
        required=True,
        default=lambda self: self.env['account.journal'].search([])
    )
    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        'daybook_analytic_account_rel',
        'daybook_id',
        'analytic_account_id',
        string='Analytic Accounts'
    )
    report_type = fields.Selection(
        [
            ('separate', 'Separate Reports (One per Analytic Account)'),
            ('combined', 'Combined Report (All Analytic Accounts Together)'),
            ('all', 'All Entries (No Analytic Filter)')
        ],
        string='Report Type',
        required=True,
        default='combined'
    )

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_from > record.date_to:
                raise UserError(_('Start Date must be before End Date.'))

    def _build_comparison_context(self, data):
        result = {}
        result['journal_ids'] = data['form'].get('journal_ids', False)
        result['state'] = data['form'].get('target_move', '')
        result['date_from'] = data['form']['date_from']
        result['date_to'] = data['form']['date_to']
        result['analytic_account_ids'] = data['form'].get('analytic_account_ids', [])
        result['report_type'] = data['form'].get('report_type', 'combined')
        return result

    def check_report(self):
        self.ensure_one()

        # Validate analytic account selection for separate/combined reports
        if self.report_type in ['separate', 'combined'] and not self.analytic_account_ids:
            raise UserError(_('Please select at least one Analytic Account for Separate or Combined reports.'))

        data = {}
        data['form'] = self.read([
            'target_move',
            'date_from',
            'date_to',
            'journal_ids',
            'analytic_account_ids',
            'report_type'
        ])[0]

        comparison_context = self._build_comparison_context(data)
        data['form']['comparison_context'] = comparison_context

        # Choose the appropriate report based on report_type
        if self.report_type == 'separate':
            return self.env.ref(
                'om_account_daybook_analytic.action_report_daybook_analytic_separate'
            ).report_action(self, data=data)
        else:
            return self.env.ref(
                'om_account_daybook_analytic.action_report_daybook_analytic_combined'
            ).report_action(self, data=data)
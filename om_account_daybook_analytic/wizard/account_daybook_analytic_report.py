from odoo import api, fields, models


class AccountDaybookReportWizard(models.TransientModel):
    _name = 'report.om_daybook_analytic.daybook_analytic_wizard'
    _description = 'Daybook Analytic Report Wizard'

    date_from = fields.Date(string='Start Date', required=True)
    date_to = fields.Date(string='End Date', required=True)
    target_move = fields.Selection([
        ('all', 'All Entries'),
        ('posted', 'Posted Entries')
    ], string='Target Moves', default='all', required=True)

    journal_ids = fields.Many2many(
        'account.journal',
        'rel_daybook_journal',  # shorter table name
        'wizard_id', 'journal_id',
        string='Journals'
    )

    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        'rel_daybook_analytic',  # shorter table name
        'wizard_id', 'analytic_id',
        string='Analytic Accounts'
    )

    company_id = fields.Many2one(
        'res.company', string='Company',
        required=True, default=lambda self: self.env.company
    )

    def _prepare_report_data(self):
        """Prepare data dict for the report."""
        return {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'target_move': self.target_move,
            'journal_ids': self.journal_ids.ids,
            'analytic_account_ids': self.analytic_account_ids.ids,
            'company_id': self.company_id.id,
        }

    def print_report_combined(self):
        """Print combined report for all selected analytic accounts."""
        data = self._prepare_report_data()
        return self.env.ref(
            'om_daybook_analytic.action_report_daybook_analytic_combined'
        ).report_action(self, data=data)

    def print_report_separate(self):
        """Print separate report per analytic account."""
        data = self._prepare_report_data()
        return self.env.ref(
            'om_daybook_analytic.action_report_daybook_analytic_separate'
        ).report_action(self, data=data)

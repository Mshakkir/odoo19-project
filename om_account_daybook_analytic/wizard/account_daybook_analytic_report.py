from odoo import api, fields, models


class AccountDaybookReportWizard(models.TransientModel):
    _name = 'report.om_daybook_analytic.report_daybook_analytic_combined'
    _description = 'Daybook Analytic Report Wizard'

    date_from = fields.Date(string='Start Date', required=True)
    date_to = fields.Date(string='End Date', required=True)
    target_move = fields.Selection([
        ('all', 'All Entries'),
        ('posted', 'Posted Entries')
    ], string='Target Moves', default='all', required=True)
    journal_ids = fields.Many2many(
        'account.journal', string='Journals', required=False)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company)
    analytic_account_ids = fields.Many2many(
        'account.analytic.account', string='Analytic Accounts')

    def _prepare_report_data(self):
        """Prepare the data dict to pass to the report."""
        return {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'target_move': self.target_move,
            'journal_ids': self.journal_ids.ids,
            'company_id': self.company_id.id,
            'analytic_account_ids': self.analytic_account_ids.ids,
        }

    def print_report_separate(self):
        """Print separate report per analytic account."""
        data = self._prepare_report_data()
        return self.env.ref(
            'om_daybook_analytic.action_report_daybook_analytic_separate'
        ).report_action(self, data=data)

    def print_report_combined(self):
        """Print combined report of all selected analytic accounts."""
        data = self._prepare_report_data()
        return self.env.ref(
            'om_daybook_analytic.action_report_daybook_analytic_combined'
        ).report_action(self, data=data)

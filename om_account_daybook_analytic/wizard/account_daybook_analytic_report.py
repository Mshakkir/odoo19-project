from odoo import api, fields, models

class DaybookAnalyticWizard(models.TransientModel):
    _name = 'daybook.analytic.wizard'
    _description = 'Daybook Analytic Report Wizard'

    date_from = fields.Date(string='Start Date', required=True)
    date_to = fields.Date(string='End Date', required=True)
    journal_ids = fields.Many2many('account.journal', string='Journals')
    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        'rel_daybook_analytic_account_rel',   # ✅ Short relation name to avoid long table error
        'wizard_id', 'analytic_id',
        string='Analytic Accounts'
    )

    def check_report(self):
        domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to)
        ]
        if self.journal_ids:
            domain.append(('journal_id', 'in', self.journal_ids.ids))
        if self.analytic_account_ids:
            domain.append(('analytic_account_id', 'in', self.analytic_account_ids.ids))

        move_lines = self.env['account.move.line'].search(domain)
        data = {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'journal_ids': self.journal_ids.ids,
            'analytic_account_ids': self.analytic_account_ids.ids,
            'lines': move_lines.ids,
        }
        return self.env.ref('daybook_analytic_report.report_daybook_analytic_pdf').report_action(self, data=data)

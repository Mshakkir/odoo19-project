from odoo import fields, models, api, _

class AccountReportGeneralLedgerAnalytic(models.TransientModel):
    _inherit = "account.report.general.ledger"

    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        string='Analytic Accounts',
        help='Filter General Ledger entries by analytic accounts.'
    )

    def _print_report(self, data):
        records, data = self._get_report_data(data)
        analytic_ids = self.read(['analytic_account_ids'])[0].get('analytic_account_ids', [])
        data['form']['analytic_account_ids'] = analytic_ids
        return self.env.ref('accounting_pdf_reports.action_report_general_ledger').with_context(
            landscape=True).report_action(records, data=data)

    def open_general_ledger_details(self):
        """Open account.move.line view filtered by analytic and date."""
        # Handle multiple wizards at once
        domain = []
        for wizard in self:
            if wizard.analytic_account_ids:
                domain.append(('analytic_account_id', 'in', wizard.analytic_account_ids.ids))
            if wizard.journal_ids:
                domain.append(('journal_id', 'in', wizard.journal_ids.ids))
            if wizard.date_from:
                domain.append(('date', '>=', wizard.date_from))
            if wizard.date_to:
                domain.append(('date', '<=', wizard.date_to))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Analytic Ledger Details'),
            'res_model': 'account.move.line',
            'views': [(False, 'tree'), (False, 'form')],
            'view_mode': 'tree,form',
            'domain': domain,
            'target': 'current',
        }

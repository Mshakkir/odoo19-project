# from odoo import fields, models, api, _
# from odoo.exceptions import UserError
#
# class AccountReportGeneralLedgerAnalytic(models.TransientModel):
#     _inherit = "account.report.general.ledger"
#
#     analytic_account_ids = fields.Many2many(
#         'account.analytic.account',
#         string='Analytic Accounts',
#         help='Filter General Ledger entries by analytic accounts.'
#     )
#
#     def _print_report(self, data):
#         """Override to pass analytic account info to custom report"""
#         records, data = self._get_report_data(data)
#         analytic_ids = self.read(['analytic_account_ids'])[0].get('analytic_account_ids', [])
#         data['form']['analytic_account_ids'] = analytic_ids
#         return self.env.ref('accounting_pdf_reports.action_report_general_ledger').with_context(
#             landscape=True).report_action(records, data=data)
#

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class AccountReportGeneralLedgerAnalytic(models.TransientModel):
    _inherit = "account.report.general.ledger"

    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        string='Analytic Accounts',
        help='Filter General Ledger entries by analytic accounts.'
    )

    def _print_report(self, data):
        """Override to pass analytic account info to custom report"""
        records, data = self._get_report_data(data)
        analytic_ids = self.read(['analytic_account_ids'])[0].get('analytic_account_ids', [])
        data['form']['analytic_account_ids'] = analytic_ids
        return self.env.ref('accounting_pdf_reports.action_report_general_ledger').with_context(
            landscape=True).report_action(records, data=data)

    def _get_filtered_move_lines(self):
        """Get move lines filtered by all criteria including analytic accounts"""
        self.ensure_one()

        # Build SQL query
        query = """
            SELECT aml.id
            FROM account_move_line aml
            JOIN account_move am ON aml.move_id = am.id
            WHERE aml.date >= %s
              AND aml.date <= %s
        """
        params = [self.date_from, self.date_to]

        # Add journal filter
        if self.journal_ids:
            query += " AND aml.journal_id IN %s"
            params.append(tuple(self.journal_ids.ids))

        # Add target move filter
        if self.target_move == 'posted':
            query += " AND am.state = 'posted'"

        # Add analytic filter
        if self.analytic_account_ids:
            analytic_conditions = []
            for analytic_id in self.analytic_account_ids.ids:
                analytic_conditions.append(f"aml.analytic_distribution::text LIKE '%\"{analytic_id}\"%'")

            if analytic_conditions:
                query += " AND (" + " OR ".join(analytic_conditions) + ")"

        # Add display account filter
        if self.display_account == 'movement':
            query += " AND (aml.debit != 0 OR aml.credit != 0)"

        query += " ORDER BY aml.account_id, aml.date, aml.id"

        self.env.cr.execute(query, params)
        result = self.env.cr.fetchall()
        return [r[0] for r in result]

    def check_report_analytic(self):
        """Open detailed view of general ledger with analytic accounts"""
        self.ensure_one()

        # Get filtered line IDs
        line_ids = self._get_filtered_move_lines()

        if not line_ids:
            raise UserError(_('No journal entries found for the selected criteria.'))

        return {
            'name': _('General Ledger Details (Analytic)'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'list',
            'view_id': self.env.ref('analytic_general_ledger.view_general_ledger_analytic_line_tree').id,
            'domain': [('id', 'in', line_ids)],
            'context': {
                'search_default_group_by_account': 1,
            },
            'target': 'current',
        }
from odoo import api, models

class ReportCashBookAnalytic(models.AbstractModel):
    _name = 'report.account_cashbook_analytic.report_cashbook_analytic'
    _description = 'Cash Book with Analytic Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Builds data context for the QWeb template."""
        if not data:
            data = {}

        docs = self.env['account.cashbook.report'].browse(docids)
        # Example placeholders: in a real case, populate from report wizard
        analytic_grouped_data = data.get('analytic_grouped_data', [])
        Accounts = data.get('Accounts', [])

        return {
            'doc_ids': docids,
            'doc_model': 'account.cashbook.report',
            'docs': docs,
            'data': data,
            'print_journal': data.get('print_journal', []),
            'analytic_account_names': data.get('analytic_account_names', []),
            'group_by_analytic': data.get('group_by_analytic', False),
            'report_type': data.get('report_type', 'separate'),
            'analytic_grouped_data': analytic_grouped_data,
            'Accounts': Accounts,
            'env': self.env,
        }

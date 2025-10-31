# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountingReport(models.TransientModel):
    _inherit = 'accounting.report'

    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        string='Warehouse Analytic Accounts',
        help='Select analytic accounts used for warehouses. If set, the report will be filtered to these analytic accounts.'
    )

    include_combined = fields.Boolean(
        string='Show Combined Warehouse Totals',
        help='If enabled and multiple analytic accounts are selected, show combined totals for selected warehouses.'
    )

    def _build_comparison_context(self, data):
        """Preserve the parent behavior."""
        result = super(AccountingReport, self)._build_comparison_context(data)
        return result

    def check_report(self):
        """Ensure our analytic filter values are included in the report data."""
        res = super(AccountingReport, self).check_report()
        data = res.get('data') or {'form': {}}
        data_form = data.get('form', {})

        read_vals = self.read(['analytic_account_ids', 'include_combined'])[0]
        data_form['analytic_account_ids'] = read_vals.get('analytic_account_ids', [])
        data_form['include_combined'] = read_vals.get('include_combined', False)
        res['data']['form'] = data_form
        return res

    def _print_report(self, data):
        """Pass our extra fields to the financial report print action."""
        read_vals = self.read([
            'date_from_cmp', 'debit_credit', 'date_to_cmp', 'filter_cmp',
            'account_report_id', 'enable_filter', 'label_filter',
            'target_move', 'analytic_account_ids', 'include_combined'
        ])[0]
        data['form'].update(read_vals)
        return self.env.ref('accounting_pdf_reports.action_report_financial').report_action(
            self, data=data, config=False
        )

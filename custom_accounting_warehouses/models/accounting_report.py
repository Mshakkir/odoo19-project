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


# keep original behavior
result = super(AccountingReport, self)._build_comparison_context(data)
return result


def check_report(self):


    res = super(AccountingReport, self).check_report()
# ensure our fields are in the data['form'] for printing
data = res.get('data') or {'form': {}}
data_form = data.get('form', {})
# fetch the current transient values and store IDs instead of record tuples
read_vals = self.read(['analytic_account_ids', 'include_combined'])[0]
# read returns many2many as list of ids
data_form['analytic_account_ids'] = read_vals.get('analytic_account_ids', [])
data_form['include_combined'] = read_vals.get('include_combined', False)
res['data']['form'] = data_form
return res


def _print_report(self, data):


# update the form with our fields so report_action gets them
read_vals = self.read(['date_from_cmp', 'debit_credit', 'date_to_cmp', 'filter_cmp',
                       'account_report_id', 'enable_filter', 'label_filter',
                       'target_move', 'analytic_account_ids', 'include_combined'])[0]
data['form'].update(read_vals)
return self.env.ref('accounting_pdf_reports.action_report_financial').report_action(self, data=data, config=False)

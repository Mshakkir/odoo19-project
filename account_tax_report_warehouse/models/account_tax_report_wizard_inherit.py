# from odoo import api, fields, models
#
# class AccountTaxReportWizard(models.TransientModel):
#     _inherit = "account.tax.report.wizard"
#
#     analytic_account_ids = fields.Many2many(
#         'account.analytic.account',
#         string="Analytic Accounts (Warehouses)",
#         help="Filter Tax Report based on selected warehouse analytic accounts."
#     )
#
#     @api.model
#     def _get_report_values(self, docids, data=None):
#         """Inject analytic filter into report context."""
#         res = super()._get_report_values(docids, data=data)
#         if data and data.get('form') and data['form'].get('analytic_account_ids'):
#             analytic_ids = data['form']['analytic_account_ids']
#             res['data']['form']['analytic_account_ids'] = analytic_ids
#         return res
# def _print_report(self):
#     form_data = self.read(['date_from', 'date_to', 'target_move', 'analytic_account_ids'])[0]
#
#     # Normalize analytic_account_ids
#     analytic_ids = form_data.get('analytic_account_ids', [])
#     if analytic_ids and isinstance(analytic_ids[0], (tuple, list)):
#         analytic_ids = analytic_ids[0][2]  # get IDs from [(6, 0, [ids])]
#     form_data['analytic_account_ids'] = analytic_ids
#
#     return self.env.ref('accounting_pdf_reports.action_report_account_tax').report_action(self, data={'form': form_data})
#
from odoo import api, fields, models


class AccountTaxReportWizard(models.TransientModel):
    _inherit = "account.tax.report.wizard"

    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        string="Analytic Accounts (Warehouses)",
        help="Filter Tax Report based on selected warehouse analytic accounts."
    )

    def _print_report(self):
        """Add analytic account filters to tax report print."""
        form_data = self.read(['date_from', 'date_to', 'target_move', 'analytic_account_ids'])[0]

        analytic_ids = []
        if form_data.get('analytic_account_ids'):
            if isinstance(form_data['analytic_account_ids'][0], (tuple, list)):
                analytic_ids = form_data['analytic_account_ids'][0][2]
            else:
                analytic_ids = form_data['analytic_account_ids']
        form_data['analytic_account_ids'] = analytic_ids

        return self.env.ref(
            'accounting_pdf_reports.action_report_account_tax'
        ).report_action(self, data={'form': form_data})


class AccountTaxReportFiltered(models.AbstractModel):
    _inherit = 'report.accounting_pdf_reports.account_tax_report'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Filter the Tax Report based on analytic accounts (warehouses)."""
        res = super()._get_report_values(docids, data=data)

        form = data.get('form', {})
        analytic_ids = form.get('analytic_account_ids', [])

        # ✅ If no analytic accounts selected → return combined report
        if not analytic_ids:
            return res

        analytic_ids = [int(i) for i in analytic_ids]

        move_line_obj = self.env['account.move.line']

        # Rebuild domain for analytic filter
        domain = [
            ('tax_line_id', '!=', False),
            ('parent_state', '=', 'posted'),
        ]

        if form.get('date_from'):
            domain.append(('date', '>=', form['date_from']))
        if form.get('date_to'):
            domain.append(('date', '<=', form['date_to']))

        # ✅ Filter based on analytic account (support both old and new analytic fields)
        domain += ['|',
            ('analytic_line_ids.account_id', 'in', analytic_ids),
            ('analytic_distribution', '!=', False),
        ]

        # Get all relevant move lines
        move_lines = move_line_obj.search(domain)

        # ✅ Manually filter JSON-based analytics
        filtered_lines = []
        for line in move_lines:
            if line.analytic_line_ids.filtered(lambda l: l.account_id.id in analytic_ids):
                filtered_lines.append(line)
            elif line.analytic_distribution:
                # Check if analytic key exists in distribution JSON
                for aid in analytic_ids:
                    if str(aid) in line.analytic_distribution.keys():
                        filtered_lines.append(line)
                        break

        # Build tax totals
        tax_summary = {}
        for line in filtered_lines:
            tax = line.tax_line_id
            if not tax:
                continue
            if tax.id not in tax_summary:
                tax_summary[tax.id] = {
                    'tax': tax,
                    'base': 0.0,
                    'amount': 0.0,
                }
            tax_summary[tax.id]['base'] += abs(line.tax_base_amount or 0.0)
            tax_summary[tax.id]['amount'] += abs(line.balance or 0.0)

        # ✅ Safely inject filtered data — don’t overwrite required keys
        res['filtered_taxes'] = list(tax_summary.values())
        res['analytic_account_ids'] = analytic_ids
        return res

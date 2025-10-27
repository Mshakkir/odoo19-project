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
        """Override the print logic to include analytic filter."""
        form_data = self.read(['date_from', 'date_to', 'target_move', 'analytic_account_ids'])[0]

        # Extract analytic IDs correctly
        analytic_ids = form_data.get('analytic_account_ids', [])
        if analytic_ids and isinstance(analytic_ids[0], (tuple, list)):
            analytic_ids = analytic_ids[0][2]
        form_data['analytic_account_ids'] = analytic_ids

        return self.env.ref(
            'accounting_pdf_reports.action_report_account_tax'
        ).report_action(self, data={'form': form_data})


class AccountTaxReportCustom(models.AbstractModel):
    _inherit = "report.accounting_pdf_reports.account_tax_report"

    @api.model
    def _get_report_values(self, docids, data=None):
        """Apply analytic filter in tax report."""
        res = super()._get_report_values(docids, data=data)
        form = data.get('form', {})

        analytic_ids = form.get('analytic_account_ids', [])
        if not analytic_ids:
            return res  # nothing to filter

        analytic_ids = [int(a) for a in analytic_ids]
        move_line_obj = self.env['account.move.line']

        domain = [
            ('tax_line_id', '!=', False),
            ('parent_state', '=', 'posted'),
            ('move_id.move_type', 'in', ['out_invoice', 'in_invoice', 'out_refund', 'in_refund']),
        ]

        if form.get('date_from'):
            domain.append(('date', '>=', form['date_from']))
        if form.get('date_to'):
            domain.append(('date', '<=', form['date_to']))

        # ✅ Analytic filters
        # Handle both analytic_line_ids and analytic_distribution safely
        analytic_domain = ['|',
            ('analytic_line_ids.account_id', 'in', analytic_ids),
            ('analytic_distribution', 'ilike', str(analytic_ids[0]))  # JSONB text search fallback
        ]
        domain += analytic_domain

        move_lines = move_line_obj.search(domain)

        # Build filtered tax summary
        tax_summary = {}
        for line in move_lines:
            tax = line.tax_line_id
            if not tax:
                continue
            if tax.id not in tax_summary:
                tax_summary[tax.id] = {
                    'tax': tax,
                    'base': 0.0,
                    'amount': 0.0,
                }
            tax_summary[tax.id]['base'] += abs(line.tax_base_amount)
            tax_summary[tax.id]['amount'] += abs(line.balance)

        # Safely replace tax data in result
        res.update({
            'Taxes': list(tax_summary.values()),
            'analytic_account_ids': analytic_ids,
        })
        return res

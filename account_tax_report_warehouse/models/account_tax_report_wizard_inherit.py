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
        """Include analytic filters when printing the tax report."""
        form_data = self.read(['date_from', 'date_to', 'target_move', 'analytic_account_ids'])[0]
        analytic_ids = form_data.get('analytic_account_ids', [])

        # Handle many2many [(6, 0, [...])] case
        if analytic_ids and isinstance(analytic_ids[0], (tuple, list)):
            analytic_ids = analytic_ids[0][2]

        form_data['analytic_account_ids'] = analytic_ids or []
        return self.env.ref(
            'accounting_pdf_reports.action_report_account_tax'
        ).report_action(self, data={'form': form_data})


class AccountTaxReportCustom(models.AbstractModel):
    _inherit = "report.accounting_pdf_reports.account_tax_report"

    @api.model
    def _get_report_values(self, docids, data=None):
        """Filter tax report lines based on analytic accounts."""
        res = super()._get_report_values(docids, data=data or {})
        form = (data or {}).get('form', {})
        analytic_ids = form.get('analytic_account_ids', [])

        # ✅ No analytic filter → return normal report
        if not analytic_ids:
            return res

        analytic_ids = [int(x) for x in analytic_ids]
        new_lines = []

        # ✅ Filter existing report lines
        for line in res.get('Lines', []):
            aml = self.env['account.move.line'].browse(line.get('id'))
            include_line = False

            # Case 1: Analytic distribution (JSONB)
            if aml.analytic_distribution:
                keys = list(aml.analytic_distribution.keys())
                if any(str(aid) in keys for aid in analytic_ids):
                    include_line = True

            # Case 2: Analytic lines (M2M)
            elif aml.analytic_line_ids:
                if any(l.account_id.id in analytic_ids for l in aml.analytic_line_ids):
                    include_line = True

            if include_line:
                new_lines.append(line)

        res['Lines'] = new_lines
        return res

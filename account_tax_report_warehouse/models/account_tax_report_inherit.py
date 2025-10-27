from odoo import api, models

class AccountTaxReportCustom(models.AbstractModel):
    _inherit = "report.accounting_pdf_reports.account_tax_report"

    @api.model
    def _get_report_values(self, docids, data=None):
        res = super()._get_report_values(docids, data=data)
        form = data.get('form', {})

        analytic_ids = form.get('analytic_account_ids', [])
        if analytic_ids:
            # Ensure analytic IDs are proper integers
            analytic_ids = [int(x) for x in analytic_ids]

            # Filter move lines in the report data
            # account_move_line in Odoo 19 CE (or similar Odoo 16+) stores analytic info
            # either in analytic_line_ids or analytic_distribution
            new_lines = []
            for line in res.get('Lines', []):
                aml = self.env['account.move.line'].browse(line.get('id'))
                # Check analytic filter
                if aml.analytic_distribution:
                    keys = list(aml.analytic_distribution.keys())
                    if any(str(aid) in keys for aid in analytic_ids):
                        new_lines.append(line)
                elif aml.analytic_line_ids:
                    if any(l.account_id.id in analytic_ids for l in aml.analytic_line_ids):
                        new_lines.append(line)

            # Replace report lines with filtered ones
            res['Lines'] = new_lines

        return res

from odoo import api, models, _
from odoo.exceptions import UserError

class ReportTaxDetail(models.AbstractModel):
    _name = 'report.accounting_pdf_reports.report_tax_detail'
    _description = 'Tax Detail Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data:
            raise UserError(_("No data provided for the report."))

        tax_id = data.get('tax_id')
        if not tax_id:
            raise UserError(_("No tax selected."))

        tax_id = int(tax_id)  # convert to int
        tax = self.env['account.tax'].browse(tax_id)
        if not tax.exists():
            raise UserError(_("Selected tax does not exist."))

        date_from = data.get('date_from')
        date_to = data.get('date_to')
        target_move = data.get('target_move')

        domain = [
            ('tax_line_id', '=', tax.id),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
        ]
        if target_move == 'posted':
            domain.append(('parent_state', '=', 'posted'))

        lines = self.env['account.move.line'].search(domain)

        return {
            'tax': tax,
            'lines': lines,
            'data': data,
        }

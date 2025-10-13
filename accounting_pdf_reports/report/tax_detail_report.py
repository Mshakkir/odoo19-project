from odoo import api, models, _

class ReportTaxDetail(models.AbstractModel):
    _name = 'report.accounting_pdf_reports.report_tax_detail'
    _description = 'Tax Detail Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        tax_id = data.get('tax_id')
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        target_move = data.get('target_move')

        if not tax_id:
            raise UserError(_("No tax selected."))

        domain = [
            ('tax_line_id', '=', tax_id),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
        ]
        if target_move == 'posted':
            domain.append(('parent_state', '=', 'posted'))

        lines = self.env['account.move.line'].search(domain)

        return {
            'tax': self.env['account.tax'].browse(tax_id),
            'lines': lines,
            'data': data,
        }

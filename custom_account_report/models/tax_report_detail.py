# # models/tax_report_detail.py
# from odoo import models, fields, api
#
# class TaxReportDetail(models.TransientModel):
#     _name = 'tax.report.detail'
#     _description = 'Tax Report Detail'
#
#     tax_id = fields.Many2one('account.tax', string="Tax")
#     invoice_id = fields.Many2one('account.move', string="Invoice")
#     partner_id = fields.Many2one('res.partner', string="Customer/Vendor")
#     date = fields.Date(string="Invoice Date")
#     amount = fields.Monetary(string="Amount", currency_field='currency_id')
#     currency_id = fields.Many2one('res.currency', string="Currency")
#
#     @api.model
#     def get_tax_details(self, tax_id, date_from=None, date_to=None):
#         domain = [('tax_line_ids.tax_id', '=', tax_id)]
#         if date_from:
#             domain.append(('invoice_date', '>=', date_from))
#         if date_to:
#             domain.append(('invoice_date', '<=', date_to))
#         moves = self.env['account.move'].search(domain)
#         lines = []
#         for move in moves:
#             for line in move.tax_line_ids.filtered(lambda l: l.tax_id.id == tax_id):
#                 lines.append({
#                     'tax_id': tax_id,
#                     'invoice_id': move.id,
#                     'partner_id': move.partner_id.id,
#                     'date': move.invoice_date,
#                     'amount': line.amount,
#                     'currency_id': move.currency_id.id,
#                 })
#         return lines

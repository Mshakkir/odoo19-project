from odoo import models, fields, api

class TaxReportDetailLine(models.TransientModel):
    _name = 'tax.report.detail.line'
    _description = 'Tax Report Detail Line'

    wizard_id = fields.Many2one('account.tax.report.wizard', string="Wizard", ondelete='cascade')

    tax_name = fields.Char(string="Tax Name")
    tax_id = fields.Many2one('account.tax', string="Tax")
    type = fields.Selection([
        ('sale', 'Sales'),
        ('purchase', 'Purchase'),
    ], string="Type")

    base_amount = fields.Monetary(string="Base Amount", currency_field='currency_id')
    tax_amount = fields.Monetary(string="Tax Amount", currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string="Currency", default=lambda self: self.env.company.currency_id.id)

    # ✅ Safe, transient-friendly compute field
    is_summary_row = fields.Boolean(string="Is Summary Row", compute='_compute_is_summary_row')

    @api.depends('tax_name')
    def _compute_is_summary_row(self):
        """Mark rows that represent total summaries."""
        for line in self:
            line.is_summary_row = line.tax_name in ['Total Sales', 'Total Purchases', 'Net VAT Due']




# from odoo import models, fields
#
# class TaxReportDetailLine(models.TransientModel):
#     _name = "tax.report.detail.line"
#     _description = "Tax Report Detail Line"
#
#     wizard_id = fields.Many2one('account.tax.report.wizard')
#     type = fields.Selection([('sale', 'Sale'), ('purchase', 'Purchase')], string='Type')
#     tax_id = fields.Many2one('account.tax', string='Tax')
#     tax_name = fields.Char(related='tax_id.name', string='Tax Name')
#     base_amount = fields.Monetary(string='Net Amount')
#     tax_amount = fields.Monetary(string='Tax Amount')
#     currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
#     move_ids = fields.Many2many('account.move', string='Invoices')
#
#     def open_moves(self):
#         """Open invoices related to this tax line"""
#         self.ensure_one()
#         return {
#             'name': 'Invoices for Tax',
#             'type': 'ir.actions.act_window',
#             'res_model': 'account.move',
#             'view_mode': 'list,form',
#             'domain': [('id', 'in', self.move_ids.ids)],
#             'target': 'current',
#         }

from odoo import models, fields, api

class TaxReportDetailLine(models.Model):
    _name = 'tax.report.detail.line'
    _description = 'Tax Report Detail Line'

    tax_name = fields.Char()
    tax_id = fields.Many2one('account.tax', string="Tax")
    type = fields.Selection([
        ('sale', 'Sales'),
        ('purchase', 'Purchase'),
    ], string="Type")
    base_amount = fields.Monetary()
    tax_amount = fields.Monetary()
    currency_id = fields.Many2one('res.currency')

    # 👇 This is the key field needed for the view
    is_summary_row = fields.Boolean(
        string="Is Summary Row",
        compute='_compute_is_summary_row',
        store=False
    )

    @api.depends('tax_name')
    def _compute_is_summary_row(self):
        """Mark total summary rows to control field visibility in view"""
        for line in self:
            line.is_summary_row = line.tax_name in [
                'Total Sales',
                'Total Purchases',
                'Net VAT Due'
            ]

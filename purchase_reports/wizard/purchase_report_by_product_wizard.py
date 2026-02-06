from odoo import models, fields

class PurchaseReportByProductWizard(models.TransientModel):
    _name = 'purchase.report.by.product.wizard'
    _description = 'Purchase Report Wizard'

    date_from = fields.Date('Date From', required=True, default=fields.Date.context_today)
    date_to = fields.Date('Date To', required=True, default=fields.Date.context_today)

    def action_generate_report(self):
        domain = [
            ('order_date', '>=', self.date_from),
            ('order_date', '<=', self.date_to)
        ]
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Report',
            'res_model': 'purchase.report.view',
            'view_mode': 'list',
            'domain': domain,
            'target': 'current',
        }
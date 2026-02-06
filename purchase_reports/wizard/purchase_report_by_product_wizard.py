from odoo import models, fields


class PurchaseReportByProductWizard(models.TransientModel):
    _name = 'purchase.report.by.product.wizard'
    _description = 'Purchase Invoice Report - By Product'

    date_from = fields.Date('From Date', required=True, default=fields.Date.context_today)
    date_to = fields.Date('To Date', required=True, default=fields.Date.context_today)
    product_ids = fields.Many2many('product.product', string='Products')
    partner_ids = fields.Many2many('res.partner', string='Vendors', domain=[('supplier_rank', '>', 0)])
    categ_ids = fields.Many2many('product.category', string='Categories')

    def action_generate_report(self):
        self.ensure_one()

        domain = [
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to)
        ]

        if self.product_ids:
            domain.append(('product_id', 'in', self.product_ids.ids))

        if self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))

        if self.categ_ids:
            domain.append(('categ_id', 'in', self.categ_ids.ids))

        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Invoice Report - By Product',
            'res_model': 'purchase.report.view',
            'view_mode': 'list,pivot',
            'domain': domain,
            'target': 'current',
            'context': {
                'search_default_group_product': 1,
            }
        }
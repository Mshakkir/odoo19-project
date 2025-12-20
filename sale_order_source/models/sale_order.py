from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    order_source = fields.Selection([
        ('erp', 'ERP'),
        ('ecommerce', 'eCommerce'),
    ], string='Order Source', compute='_compute_order_source', store=True, readonly=True)

    @api.depends('website_id')
    def _compute_order_source(self):
        """Compute order source based on website_id"""
        for order in self:
            if order.website_id:
                order.order_source = 'ecommerce'
            else:
                order.order_source = 'erp'

from odoo import models, fields

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    stock_move_ids = fields.One2many(
        'stock.move', 'purchase_id', string='Stock Moves', readonly=True)

    sale_line_ids = fields.One2many(
        'sale.order.line', compute='_compute_sale_lines', string='Sale Lines', readonly=True)

    purchase_line_ids = fields.One2many(
        'purchase.order.line', 'order_id', string='Purchase Lines', readonly=True)

    def _compute_sale_lines(self):
        for order in self:
            product_ids = order.order_line.mapped('product_id').ids
            order.sale_line_ids = self.env['sale.order.line'].search([
                ('product_id', 'in', product_ids)
            ])

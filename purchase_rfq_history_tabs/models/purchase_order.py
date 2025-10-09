from odoo import models, fields, api

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # One2many of stock moves related to this purchase order
    stock_move_ids = fields.One2many(
        'stock.move', compute='_compute_stock_moves',
        string='Stock Moves', readonly=True
    )

    # One2many of sale lines for products in this purchase order
    sale_line_ids = fields.One2many(
        'sale.order.line', compute='_compute_sale_lines',
        string='Sale Lines', readonly=True
    )

    # One2many of purchase lines (standard)
    purchase_line_ids = fields.One2many(
        'purchase.order.line', 'order_id',
        string='Purchase Lines', readonly=True
    )

    @api.depends('order_line')
    def _compute_stock_moves(self):
        for order in self:
            moves = self.env['stock.move'].search([
                ('purchase_line_id.order_id', '=', order.id)
            ])
            order.stock_move_ids = moves

    @api.depends('order_line.product_id')
    def _compute_sale_lines(self):
        for order in self:
            product_ids = order.order_line.mapped('product_id').ids
            sale_lines = self.env['sale.order.line'].search([
                ('product_id', 'in', product_ids)
            ])
            order.sale_line_ids = sale_lines

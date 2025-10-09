from odoo import models, fields

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # Stock Moves related to this purchase order
    stock_move_ids = fields.One2many(
        'stock.move', compute='_compute_stock_moves', readonly=True,
        string='Stock Moves'
    )

    # Sale Order Lines related to products in this purchase order
    sale_line_ids = fields.One2many(
        'sale.order.line', compute='_compute_sale_lines', readonly=True,
        string='Sale Lines'
    )

    # Purchase Order Lines of this order
    purchase_line_ids = fields.One2many(
        'purchase.order.line', 'order_id', readonly=True,
        string='Purchase Lines'
    )

    def _compute_stock_moves(self):
        for order in self:
            moves = self.env['stock.move'].search([
                ('purchase_line_id.order_id', '=', order.id)
            ])
            order.stock_move_ids = moves

    def _compute_sale_lines(self):
        for order in self:
            product_ids = order.order_line.mapped('product_id').ids
            order.sale_line_ids = self.env['sale.order.line'].search([
                ('product_id', 'in', product_ids)
            ])

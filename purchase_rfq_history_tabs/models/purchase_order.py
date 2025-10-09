from odoo import models, fields, api

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    stock_move_ids = fields.One2many(
        'stock.move', compute='_compute_stock_moves', string='Stock Moves', readonly=True)
    sale_line_ids = fields.One2many(
        'sale.order.line', compute='_compute_sale_lines', string='Sales Lines', readonly=True)
    purchase_line_ids = fields.One2many(
        'purchase.order.line', compute='_compute_purchase_lines', string='Purchase Lines', readonly=True)

    @api.depends('order_line.product_id')
    def _compute_stock_moves(self):
        for order in self:
            product_ids = order.order_line.mapped('product_id.id')
            moves = self.env['stock.move'].search([('product_id', 'in', product_ids)])
            order.stock_move_ids = moves

    @api.depends('order_line.product_id')
    def _compute_sale_lines(self):
        for order in self:
            product_ids = order.order_line.mapped('product_id.id')
            sales = self.env['sale.order.line'].search([('product_id', 'in', product_ids)])
            order.sale_line_ids = sales

    @api.depends('order_line.product_id')
    def _compute_purchase_lines(self):
        for order in self:
            product_ids = order.order_line.mapped('product_id.id')
            purchases = self.env['purchase.order.line'].search([
                ('product_id', 'in', product_ids),
                ('order_id.state', '=', 'purchase'),
            ])
            order.purchase_line_ids = purchases

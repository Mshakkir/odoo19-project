from odoo import models, fields

class ProductHistoryWizard(models.TransientModel):
    _name = 'product.history.wizard'
    _description = 'Product History Wizard'

    product_id = fields.Many2one('product.product', string='Product', required=True)

    stock_move_ids = fields.One2many(
        'stock.move',
        compute='_compute_stock_moves',
        string='Stock Moves'
    )
    purchase_line_ids = fields.One2many(
        'purchase.order.line',
        compute='_compute_purchase_lines',
        string='Purchase History'
    )
    sale_line_ids = fields.One2many(
        'sale.order.line',
        compute='_compute_sale_lines',
        string='Sales History'
    )

    def _compute_stock_moves(self):
        for wiz in self:
            wiz.stock_move_ids = self.env['stock.move'].search(
                [('product_id', '=', wiz.product_id.id)],
                limit=50,
                order='date desc'
            )

    def _compute_purchase_lines(self):
        for wiz in self:
            wiz.purchase_line_ids = self.env['purchase.order.line'].search(
                [('product_id', '=', wiz.product_id.id)],
                limit=50,
                order='order_id.date_order desc'
            )

    def _compute_sale_lines(self):
        for wiz in self:
            wiz.sale_line_ids = self.env['sale.order.line'].search(
                [('product_id', '=', wiz.product_id.id)],
                limit=50,
                order='order_id.date_order desc'
            )

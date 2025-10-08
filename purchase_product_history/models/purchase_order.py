from odoo import models, fields, api
from datetime import datetime, timedelta


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    # Computed fields for history
    purchase_history_ids = fields.Many2many(
        'purchase.order.line',
        compute='_compute_product_history',
        string='Purchase History',
        store=False
    )
    stock_move_ids = fields.Many2many(
        'stock.move',
        compute='_compute_product_history',
        string='Stock History',
        store=False
    )
    sale_order_line_ids = fields.Many2many(
        'sale.order.line',
        compute='_compute_product_history',
        string='Sale History',
        store=False
    )

    # Count fields
    purchase_history_count = fields.Integer(
        compute='_compute_product_history',
        string='Purchase Count',
        store=False
    )
    stock_history_count = fields.Integer(
        compute='_compute_product_history',
        string='Stock Count',
        store=False
    )
    sale_history_count = fields.Integer(
        compute='_compute_product_history',
        string='Sale Count',
        store=False
    )

    # Summary fields
    last_purchase_price = fields.Float(
        compute='_compute_product_history',
        string='Last Price',
        digits='Product Price',
        store=False
    )
    avg_purchase_price = fields.Float(
        compute='_compute_product_history',
        string='Avg Price',
        digits='Product Price',
        store=False
    )
    total_purchased_qty = fields.Float(
        compute='_compute_product_history',
        string='Total Purchased',
        digits='Product Unit of Measure',
        store=False
    )
    total_sold_qty = fields.Float(
        compute='_compute_product_history',
        string='Total Sold',
        digits='Product Unit of Measure',
        store=False
    )
    current_stock_qty = fields.Float(
        compute='_compute_product_history',
        string='On Hand',
        digits='Product Unit of Measure',
        store=False
    )
    last_purchase_date = fields.Datetime(
        compute='_compute_product_history',
        string='Last Purchase',
        store=False
    )

    @api.depends('product_id')
    def _compute_product_history(self):
        """Compute product, stock, and sale history"""
        for line in self:
            if not line.product_id:
                line.purchase_history_ids = False
                line.stock_move_ids = False
                line.sale_order_line_ids = False
                line.purchase_history_count = 0
                line.stock_history_count = 0
                line.sale_history_count = 0
                line.last_purchase_price = 0.0
                line.avg_purchase_price = 0.0
                line.total_purchased_qty = 0.0
                line.total_sold_qty = 0.0
                line.current_stock_qty = 0.0
                line.last_purchase_date = False
                continue

            # Get date limit (last 12 months)
            date_limit = datetime.now() - timedelta(days=365)

            # === PURCHASE HISTORY ===
            purchase_lines = self.env['purchase.order.line'].search([
                ('product_id', '=', line.product_id.id),
                ('id', '!=', line.id),
                ('state', 'in', ['purchase', 'done']),
            ], limit=200)

            # Filter manually by order's approval date
            purchase_lines = purchase_lines.filtered(
                lambda pl: pl.order_id.date_approve and pl.order_id.date_approve >= date_limit
            )

            # Sort manually by order date (descending)
            purchase_lines = purchase_lines.sorted(
                key=lambda pl: pl.order_id.date_approve or datetime.min,
                reverse=True
            )

            line.purchase_history_ids = purchase_lines
            line.purchase_history_count = len(purchase_lines)

            if purchase_lines:
                last_line = purchase_lines[0]
                line.last_purchase_price = last_line.price_unit
                line.last_purchase_date = last_line.order_id.date_approve

                # Average price & total purchased qty
                total_price = sum(purchase_lines.mapped('price_unit'))
                line.avg_purchase_price = total_price / len(purchase_lines)
                line.total_purchased_qty = sum(purchase_lines.mapped('product_qty'))
            else:
                line.last_purchase_price = 0.0
                line.avg_purchase_price = 0.0
                line.total_purchased_qty = 0.0
                line.last_purchase_date = False

            # === STOCK HISTORY ===
            stock_moves = self.env['stock.move'].search([
                ('product_id', '=', line.product_id.id),
                ('state', '=', 'done'),
                ('date', '>=', date_limit)
            ], limit=100, order='date desc')

            line.stock_move_ids = stock_moves
            line.stock_history_count = len(stock_moves)
            line.current_stock_qty = line.product_id.qty_available

            # === SALE HISTORY ===
            sale_lines = self.env['sale.order.line'].search([
                ('product_id', '=', line.product_id.id),
                ('state', 'in', ['sale', 'done']),
            ], limit=200)

            # Filter manually by order date
            sale_lines = sale_lines.filtered(
                lambda sl: sl.order_id.date_order and sl.order_id.date_order >= date_limit
            )

            # Sort manually
            sale_lines = sale_lines.sorted(
                key=lambda sl: sl.order_id.date_order or datetime.min,
                reverse=True
            )

            line.sale_order_line_ids = sale_lines
            line.sale_history_count = len(sale_lines)
            line.total_sold_qty = sum(sale_lines.mapped('product_uom_qty'))

    # === ACTION BUTTONS ===
    def action_view_purchase_history(self):
        self.ensure_one()
        return {
            'name': f'Purchase History - {self.product_id.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order.line',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.purchase_history_ids.ids)],
            'context': {'create': False, 'edit': False, 'delete': False},
        }

    def action_view_stock_history(self):
        self.ensure_one()
        return {
            'name': f'Stock History - {self.product_id.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.move',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.stock_move_ids.ids)],
            'context': {'create': False, 'edit': False, 'delete': False},
        }

    def action_view_sale_history(self):
        self.ensure_one()
        return {
            'name': f'Sale History - {self.product_id.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order.line',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.sale_order_line_ids.ids)],
            'context': {'create': False, 'edit': False, 'delete': False},
        }

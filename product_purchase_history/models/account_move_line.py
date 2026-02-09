# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model
    def get_product_purchase_history(self, product_id):
        """
        Fetch purchase history for a given product
        Returns list of purchase order lines with supplier info
        """
        if not product_id:
            return []

        # Search for purchase order lines with this product
        purchase_lines = self.env['purchase.order.line'].search([
            ('product_id', '=', product_id),
            ('order_id.state', 'in', ['purchase', 'done'])
        ], order='date_order desc', limit=50)

        history = []
        for line in purchase_lines:
            history.append({
                'id': line.id,
                'order_name': line.order_id.name or '',
                'partner_name': line.order_id.partner_id.name if line.order_id.partner_id else '',
                'date_order': line.date_order.strftime('%Y-%m-%d') if line.date_order else '',
                'product_qty': line.product_qty,
                'product_uom': line.product_uom_id.name if line.product_uom_id else '',  # Changed from product_uom
                'price_unit': line.price_unit,
                'price_subtotal': line.price_subtotal,
                'currency': line.currency_id.symbol if line.currency_id else '',  # Changed from order_id.currency_id
                'state': line.order_id.state,
            })

        return history
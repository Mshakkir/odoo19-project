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
        # Note: state is on purchase.order, not purchase.order.line
        purchase_lines = self.env['purchase.order.line'].search([
            ('product_id', '=', product_id),
            ('order_id.state', 'in', ['purchase', 'done'])  # Order state
        ], order='date_order desc', limit=50)  # date_order works directly in order clause

        history = []
        for line in purchase_lines:
            # Safely get the date
            date_str = ''
            if line.date_order:
                date_str = line.date_order.strftime('%Y-%m-%d')

            history.append({
                'id': line.id,
                'order_name': line.order_id.name or '',
                'partner_name': line.order_id.partner_id.name if line.order_id.partner_id else '',
                'date_order': date_str,
                'product_qty': line.product_qty,
                'product_uom': line.product_uom.name if line.product_uom else '',
                'price_unit': line.price_unit,
                'price_subtotal': line.price_subtotal,
                'currency': line.order_id.currency_id.symbol if line.order_id.currency_id else '',
                'state': line.order_id.state,  # Get state from order
            })

        return history
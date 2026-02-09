# # -*- coding: utf-8 -*-
# from odoo import api, fields, models
#
#
# class AccountMoveLine(models.Model):
#     _inherit = 'account.move.line'
#
#     @api.model
#     def get_product_purchase_history(self, product_id):
#         """
#         Fetch purchase history for a given product
#         Returns list of purchase order lines with supplier info
#         """
#         if not product_id:
#             return []
#
#         # Search for purchase order lines with this product
#         purchase_lines = self.env['purchase.order.line'].search([
#             ('product_id', '=', product_id),
#             ('order_id.state', 'in', ['purchase', 'done'])
#         ], order='date_order desc', limit=50)
#
#         history = []
#         for line in purchase_lines:
#             history.append({
#                 'id': line.id,
#                 'order_name': line.order_id.name or '',
#                 'partner_name': line.order_id.partner_id.name if line.order_id.partner_id else '',
#                 'date_order': line.date_order.strftime('%Y-%m-%d') if line.date_order else '',
#                 'product_qty': line.product_qty,
#                 'product_uom': line.product_uom_id.name if line.product_uom_id else '',  # Changed from product_uom
#                 'price_unit': line.price_unit,
#                 'price_subtotal': line.price_subtotal,
#                 'currency': line.currency_id.symbol if line.currency_id else '',  # Changed from order_id.currency_id
#                 'state': line.order_id.state,
#             })
#
#         return history

# -*- coding: utf-8 -*-
from odoo import api, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model
    def get_product_purchase_history(self, product_id):
        """
        Fetch purchase history from:
        1) Purchase Orders
        2) Direct Vendor Bills (Purchase Invoices)
        """
        if not product_id:
            return []

        history = []

        # --------------------------------------------------
        # 1️⃣ PURCHASE ORDER LINES
        # --------------------------------------------------
        po_lines = self.env['purchase.order.line'].search([
            ('product_id', '=', product_id),
            ('order_id.state', 'in', ['purchase', 'done'])
        ], order='order_id.date_order desc', limit=50)

        for line in po_lines:
            history.append({
                'id': f'po_{line.id}',
                'source': 'PO',
                'reference': line.order_id.name or '',
                'partner_name': line.order_id.partner_id.name or '',
                'date': line.order_id.date_order.strftime('%Y-%m-%d') if line.order_id.date_order else '',
                'qty': line.product_qty,
                'uom': line.product_uom_id.name or '',
                'price_unit': line.price_unit,
                'subtotal': line.price_subtotal,
                'currency': line.currency_id.symbol or '',
                'state': line.order_id.state,
            })

        # --------------------------------------------------
        # 2️⃣ DIRECT VENDOR BILLS (PURCHASE INVOICES)
        # --------------------------------------------------
        bill_lines = self.env['account.move.line'].search([
            ('product_id', '=', product_id),
            ('move_id.move_type', '=', 'in_invoice'),
            ('move_id.state', '=', 'posted'),
        ], order='move_id.invoice_date desc', limit=50)

        for line in bill_lines:
            history.append({
                'id': f'bill_{line.id}',
                'source': 'BILL',
                'reference': line.move_id.name or '',
                'partner_name': line.move_id.partner_id.name or '',
                'date': line.move_id.invoice_date.strftime('%Y-%m-%d') if line.move_id.invoice_date else '',
                'qty': line.quantity,
                'uom': line.product_uom_id.name or '',
                'price_unit': line.price_unit,
                'subtotal': line.price_subtotal,
                'currency': line.currency_id.symbol or '',
                'state': 'posted',
            })

        # --------------------------------------------------
        # Sort by date (latest first)
        # --------------------------------------------------
        history.sort(key=lambda x: x['date'] or '', reverse=True)

        return history

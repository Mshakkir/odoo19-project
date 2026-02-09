# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model
    def get_product_purchase_history(self, product_id):
        """
        Fetch purchase history for a given product from both purchase orders and invoices
        Returns combined list with supplier info and tax details
        """
        if not product_id:
            return []

        history = []

        # 1. Get data from PURCHASE INVOICES (Vendor Bills)
        invoice_lines = self.env['account.move.line'].search([
            ('product_id', '=', product_id),
            ('move_id.move_type', 'in', ['in_invoice', 'in_refund']),
            ('move_id.state', 'in', ['posted']),
            ('display_type', '=', False),
        ], order='move_id.invoice_date desc', limit=30)

        for line in invoice_lines:
            # Get tax information
            tax_names = ', '.join(line.tax_ids.mapped('name')) if line.tax_ids else 'No Tax'
            tax_amount = sum(line.tax_ids.mapped(lambda t: line.price_subtotal * (t.amount / 100)))
            price_total = line.price_subtotal + tax_amount

            history.append({
                'id': f'inv_{line.id}',
                'order_name': line.move_id.name or '',
                'source_type': 'Invoice',
                'partner_name': line.move_id.partner_id.name if line.move_id.partner_id else '',
                'date_order': line.move_id.invoice_date.strftime('%Y-%m-%d') if line.move_id.invoice_date else '',
                'product_qty': line.quantity,
                'product_uom': line.product_uom_id.name if line.product_uom_id else '',
                'price_unit': line.price_unit,
                'price_subtotal': line.price_subtotal,
                'tax_names': tax_names,
                'tax_amount': tax_amount,
                'price_total': price_total,
                'currency': line.currency_id.symbol if line.currency_id else '',
                'state': line.move_id.state,
                'invoice_type': 'Credit Note' if line.move_id.move_type == 'in_refund' else 'Bill',
                'sort_date': line.move_id.invoice_date or fields.Date.today(),
            })

        # 2. Get data from PURCHASE ORDERS
        purchase_lines = self.env['purchase.order.line'].search([
            ('product_id', '=', product_id),
            ('order_id.state', 'in', ['purchase', 'done'])
        ], order='date_order desc', limit=30)

        for line in purchase_lines:
            # Get tax information from purchase order
            tax_names = ', '.join(line.taxes_id.mapped('name')) if line.taxes_id else 'No Tax'
            # Tax amount is already calculated in price_tax field
            tax_amount = line.price_tax if hasattr(line, 'price_tax') else 0
            price_total = line.price_subtotal + tax_amount

            history.append({
                'id': f'po_{line.id}',
                'order_name': line.order_id.name or '',
                'source_type': 'Purchase Order',
                'partner_name': line.order_id.partner_id.name if line.order_id.partner_id else '',
                'date_order': line.date_order.strftime('%Y-%m-%d') if line.date_order else '',
                'product_qty': line.product_qty,
                'product_uom': line.product_uom.name if line.product_uom else '',
                'price_unit': line.price_unit,
                'price_subtotal': line.price_subtotal,
                'tax_names': tax_names,
                'tax_amount': tax_amount,
                'price_total': price_total,
                'currency': line.currency_id.symbol if line.currency_id else '',
                'state': line.order_id.state,
                'invoice_type': 'Purchase Order',
                'sort_date': line.date_order or fields.Date.today(),
            })

        # Sort all records by date (newest first)
        history.sort(key=lambda x: x['sort_date'], reverse=True)

        # Remove sort_date as it's not needed in frontend
        for item in history:
            item.pop('sort_date', None)

        # Return top 50 records
        return history[:50]
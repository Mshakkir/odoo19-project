# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model
    def get_product_purchase_history(self, product_id):
        """
        Fetch purchase history for a given product from vendor bills
        Returns list of invoice lines with supplier info
        """
        if not product_id:
            return []

        # Search for vendor bill lines with this product
        # Remove display_type filter as it might be blocking results
        invoice_lines = self.env['account.move.line'].search([
            ('product_id', '=', product_id),
            ('move_id.move_type', '=', 'in_invoice'),
            ('move_id.state', 'in', ['draft', 'posted']),  # Include both draft and posted
            ('exclude_from_invoice_tab', '=', False),  # Exclude non-invoice lines
        ], order='move_id.date desc', limit=50)

        history = []
        for line in invoice_lines:
            # Skip lines without product (like section/note lines)
            if not line.product_id:
                continue

            history.append({
                'id': line.id,
                'order_name': line.move_id.name or '',
                'partner_name': line.move_id.partner_id.name if line.move_id.partner_id else '',
                'date_order': line.move_id.invoice_date.strftime('%Y-%m-%d') if line.move_id.invoice_date else (
                    line.move_id.date.strftime('%Y-%m-%d') if line.move_id.date else ''),
                'product_qty': line.quantity,
                'product_uom': line.product_uom_id.name if line.product_uom_id else '',
                'price_unit': line.price_unit,
                'price_subtotal': line.price_subtotal,
                'currency': line.currency_id.symbol if line.currency_id else '',
                'state': line.move_id.state,
            })

        return history
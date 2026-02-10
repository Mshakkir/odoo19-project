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
#         Fetch purchase history for a given product from vendor bills
#         Returns list of invoice lines with supplier info
#         """
#         if not product_id:
#             return []
#
#         # Search for vendor bill lines with this product
#         invoice_lines = self.env['account.move.line'].search([
#             ('product_id', '=', product_id),
#             ('move_id.move_type', '=', 'in_invoice'),
#         ], limit=50)
#
#         history = []
#         for line in invoice_lines:
#             # Skip if move is not in valid state
#             if line.move_id.state not in ['draft', 'posted']:
#                 continue
#
#             # Skip lines without product
#             if not line.product_id:
#                 continue
#
#             # Skip ONLY section and note lines, NOT product lines
#             if hasattr(line, 'display_type') and line.display_type in ['line_section', 'line_note']:
#                 continue
#
#             history.append({
#                 'id': line.id,
#                 'order_name': line.move_id.name or '',
#                 'partner_name': line.move_id.partner_id.name if line.move_id.partner_id else '',
#                 'date_order': line.move_id.invoice_date.strftime('%Y-%m-%d') if line.move_id.invoice_date else '',
#                 'product_qty': line.quantity,
#                 'product_uom': line.product_uom_id.name if line.product_uom_id else '',
#                 'price_unit': line.price_unit,
#                 'price_subtotal': line.price_subtotal,
#                 'currency': line.currency_id.symbol if line.currency_id else '',
#                 'state': line.move_id.state,
#             })
#
#         # Sort by date in Python (descending)
#         history.sort(key=lambda x: x['date_order'], reverse=True)
#
#         return history

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
        invoice_lines = self.env['account.move.line'].search([
            ('product_id', '=', product_id),
            ('move_id.move_type', '=', 'in_invoice'),
        ], limit=50)

        history = []
        for line in invoice_lines:
            # Skip if move is not in valid state
            if line.move_id.state not in ['draft', 'posted']:
                continue

            # Skip lines without product
            if not line.product_id:
                continue

            # Skip ONLY section and note lines, NOT product lines
            if hasattr(line, 'display_type') and line.display_type in ['line_section', 'line_note']:
                continue

            # Get tax names
            tax_names = ', '.join(line.tax_ids.mapped('name')) if line.tax_ids else ''

            # Calculate tax amount
            tax_amount = line.price_total - line.price_subtotal

            history.append({
                'id': line.id,
                'order_name': line.move_id.name or '',
                'partner_name': line.move_id.partner_id.name if line.move_id.partner_id else '',
                'date_order': line.move_id.invoice_date.strftime('%Y-%m-%d') if line.move_id.invoice_date else '',
                'product_qty': line.quantity,
                'product_uom': line.product_uom_id.name if line.product_uom_id else '',
                'price_unit': line.price_unit,
                'price_subtotal': line.price_subtotal,
                'tax_name': tax_names,
                'tax_amount': tax_amount,
                'price_total': line.price_total,
                'currency': line.currency_id.symbol if line.currency_id else '',
                'state': line.move_id.state,
            })

        # Sort by date in Python (descending)
        history.sort(key=lambda x: x['date_order'], reverse=True)

        return history
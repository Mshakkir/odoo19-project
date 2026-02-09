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
#         Fetch purchase history for a given product from purchase invoices
#         Returns list of invoice lines with supplier info and tax details
#         """
#         if not product_id:
#             return []
#
#         # Search for vendor bill lines with this product
#         # in_invoice = Vendor Bill, in_refund = Vendor Credit Note
#         invoice_lines = self.env['account.move.line'].search([
#             ('product_id', '=', product_id),
#             ('move_id.move_type', 'in', ['in_invoice', 'in_refund']),
#             ('move_id.state', 'in', ['posted']),  # Only posted invoices
#             ('display_type', '=', False),  # Exclude section and note lines
#         ], order='move_id.invoice_date desc', limit=50)
#
#         history = []
#         for line in invoice_lines:
#             # Get tax information
#             tax_names = ', '.join(line.tax_ids.mapped('name')) if line.tax_ids else 'No Tax'
#             tax_amount = sum(line.tax_ids.mapped(lambda t: line.price_subtotal * (t.amount / 100)))
#
#             # Calculate total with tax
#             price_total = line.price_subtotal + tax_amount
#
#             history.append({
#                 'id': line.id,
#                 'order_name': line.move_id.name or '',
#                 'source_type': 'Invoice',  # To distinguish from PO if needed later
#                 'partner_name': line.move_id.partner_id.name if line.move_id.partner_id else '',
#                 'date_order': line.move_id.invoice_date.strftime('%Y-%m-%d') if line.move_id.invoice_date else '',
#                 'product_qty': line.quantity,
#                 'product_uom': line.product_uom_id.name if line.product_uom_id else '',
#                 'price_unit': line.price_unit,
#                 'price_subtotal': line.price_subtotal,
#                 'tax_names': tax_names,
#                 'tax_amount': tax_amount,
#                 'price_total': price_total,
#                 'currency': line.currency_id.symbol if line.currency_id else '',
#                 'state': line.move_id.state,
#                 'invoice_type': 'Credit Note' if line.move_id.move_type == 'in_refund' else 'Bill',
#             })
#
#         return history
# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model
    def get_product_purchase_history(self, product_id):
        """
        Fetch purchase history for a given product from purchase invoices
        SIMPLIFIED VERSION - minimal filters, maximum compatibility
        """
        if not product_id:
            return []

        # Very simple search - just product and vendor bill type
        invoice_lines = self.env['account.move.line'].search([
            ('product_id', '=', product_id),
            ('move_id.move_type', 'in', ['in_invoice', 'in_refund']),
        ], order='move_id.invoice_date desc, id desc', limit=50)

        history = []
        for line in invoice_lines:
            # Skip if this is not a real product line
            if not line.product_id or line.price_subtotal == 0:
                continue

            # Get tax information
            tax_names = ', '.join(line.tax_ids.mapped('name')) if line.tax_ids else 'No Tax'

            # Calculate tax amount
            tax_amount = 0
            if line.tax_ids:
                for tax in line.tax_ids:
                    if tax.amount_type == 'percent':
                        tax_amount += line.price_subtotal * (tax.amount / 100)
                    elif tax.amount_type == 'fixed':
                        tax_amount += tax.amount * line.quantity

            price_total = line.price_subtotal + tax_amount

            # Determine invoice type
            if line.move_id.move_type == 'in_refund':
                invoice_type = 'Credit Note'
            else:
                invoice_type = 'Bill'

            # State label
            state_label = dict(line.move_id._fields['state'].selection).get(line.move_id.state, line.move_id.state)

            history.append({
                'id': line.id,
                'order_name': line.move_id.name or f'Draft ({line.move_id.id})',
                'source_type': 'Invoice',
                'partner_name': line.move_id.partner_id.name if line.move_id.partner_id else 'Unknown Vendor',
                'date_order': line.move_id.invoice_date.strftime('%Y-%m-%d') if line.move_id.invoice_date else (
                    line.move_id.create_date.strftime('%Y-%m-%d') if line.move_id.create_date else 'No Date'),
                'product_qty': line.quantity,
                'product_uom': line.product_uom_id.name if line.product_uom_id else 'Units',
                'price_unit': line.price_unit,
                'price_subtotal': line.price_subtotal,
                'tax_names': tax_names,
                'tax_amount': tax_amount,
                'price_total': price_total,
                'currency': line.currency_id.symbol if line.currency_id else line.move_id.currency_id.symbol if line.move_id.currency_id else '',
                'state': line.move_id.state,
                'invoice_type': invoice_type,
            })

        return history
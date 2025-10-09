# -*- coding: utf-8 -*-

from odoo import api, fields, models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def action_open_purchase_history(self):
        """Open purchase history for the product in this line"""
        self.ensure_one()

        if not self.product_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Warning',
                    'message': 'No product selected',
                    'type': 'warning',
                }
            }

        # Get the product template
        product_template = self.product_id.product_tmpl_id

        wizard = self.env['product.purchase.history'].create({
            'product_id': product_template.id,
        })

        # Search for all purchase lines of this product (all variants)
        variant_ids = product_template.product_variant_ids.ids
        purchase_lines = self.env['purchase.order.line'].search([
            ('product_id', 'in', variant_ids),
            ('order_id.state', 'in', ['purchase', 'done'])
        ], order='date_planned desc')

        history_lines = []
        for line in purchase_lines:
            history_lines.append((0, 0, {
                'po_number': line.order_id.name,
                'vendor': line.order_id.partner_id.name,
                'po_date': line.order_id.date_order,
                'quantity': line.product_qty,
                'unit_price': line.price_unit,
            }))

        wizard.line_ids = history_lines

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'product.purchase.history',
            'view_mode': 'form',
            'target': 'new',
            'name': 'Product Purchase History',
            'res_id': wizard.id,
            'view_id': self.env.ref('ps_purchase_history.product_history_view').id,
        }
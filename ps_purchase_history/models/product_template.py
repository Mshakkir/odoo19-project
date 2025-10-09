# -*- coding: utf-8 -*-


from odoo import api, fields, models


class Purchase(models.Model):
    _inherit = 'product.template'


    def open_purchase_product_history_wizard(self):
        self.ensure_one()

        wizard = self.env['product.purchase.history'].create({
            'product_id': self.id,
        })

        variant_ids = self.product_variant_ids.ids
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



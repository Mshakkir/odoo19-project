# -*- coding: utf-8 -*-

from odoo import models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def action_view_product_list(self):
        """
        Opens the Product List view filtered by the current product
        """
        self.ensure_one()

        if not self.product_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Warning',
                    'message': 'No product selected in this line.',
                    'type': 'warning',
                    'sticky': False,
                }
            }

        # Get the product list view
        list_view = self.env.ref('product.product_template_product_list', raise_if_not_found=False)
        form_view = self.env.ref('product.product_template_only_form_view', raise_if_not_found=False)
        search_view = self.env.ref('product.product_template_search_view', raise_if_not_found=False)

        return {
            'name': f'Product - {self.product_id.display_name}',
            'type': 'ir.actions.act_window',
            'res_model': 'product.template',
            'view_mode': 'list,form',
            'views': [
                (list_view.id if list_view else False, 'list'),
                (form_view.id if form_view else False, 'form')
            ],
            'search_view_id': search_view.id if search_view else False,
            'domain': [('id', '=', self.product_id.product_tmpl_id.id)],
            'res_id': self.product_id.product_tmpl_id.id,
            'context': {
                'search_default_id': self.product_id.product_tmpl_id.id,
            },
            'target': 'current',
        }



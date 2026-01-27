# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def action_view_product_stock_ledger(self):
        """
        Opens the Product Stock Ledger list view filtered by the current product
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

        return {
            'name': f'Stock Ledger - {self.product_id.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.valuation.layer',
            'view_mode': 'list,form',
            'domain': [('product_id', '=', self.product_id.id)],
            'context': {
                'default_product_id': self.product_id.id,
            },
            'target': 'current',
        }
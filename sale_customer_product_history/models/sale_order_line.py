# -*- coding: utf-8 -*-
##############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Vishnu KP (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################from odoo import models, fields, api
from odoo import models, fields, api

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def action_view_product_history(self):
        product_ids = self.mapped('product_id.id')
        tree_view = self.env.ref('sale.view_order_line_tree')  # Default tree view

        return {
            'name': 'Product History',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order.line',
            'view_mode': 'tree',
            'views': [(tree_view.id, 'tree')],
            'domain': [('product_id', 'in', product_ids)],
            'target': 'current',
            'context': self.env.context,
        }

# from odoo import models
#
# class SaleOrderLine(models.Model):
#     """Inherit sale.order.line to add a button/action that opens
#        a transient wizard showing previous sales of this product
#        for the current customer.
#     """
#     _inherit = 'sale.order.line'
#
#     def get_product_history_data(self):
#         """Return an ir.actions.act_window for a transient record that contains
#         the list of previous sale orders (state in sale/done) for the
#         current order.partner_id and this product.
#         """
#         self.ensure_one()
#         if not self.product_id:
#             return {}
#
#         partner = self.order_id.partner_id
#         # Find all sale orders for the same customer that are confirmed or done
#         orders = self.env['sale.order'].search([
#             ('partner_id', '=', partner.id),
#             ('state', 'in', ('sale', 'done')),
#         ], order='date_order desc')
#
#         values = []
#         for order in orders:
#             for line in order.order_line:
#                 if line.product_id == self.product_id:
#                     values.append((0, 0, {
#                         'sale_order_id': order.id,
#                         'history_price': line.price_unit,
#                         'history_qty': line.product_uom_qty,
#                         'history_total': order.amount_total,
#                     }))
#
#         # Create a new transient record in the wizard model
#         history = self.env['product.sale.order.history'].create({
#             'product_id': self.product_id.id,
#             'product_sale_history_ids': values,
#         })
#
#         return {
#             'name': 'Customer Product Sales History',
#             'type': 'ir.actions.act_window',
#             'res_model': 'product.sale.order.history',
#             'view_mode': 'form',
#             # FIX: Correct XML reference
#             'view_id': self.env.ref('sale_customer_product_history.product_sale_order_history_view_form').id,
#             'res_id': history.id,
#             'target': 'new',
#         }

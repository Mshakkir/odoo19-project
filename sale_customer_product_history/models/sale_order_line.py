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
##############################################################################
from odoo import models, api


class SaleOrderLine(models.Model):
    """ Inherit sale.order.line to add a button / action that opens
        a transient wizard showing previous sales of this product for
        the current customer.
    """
    _inherit = 'sale.order.line'

    def get_product_history_data(self):
        """Return an ir.actions.act_window for a transient record that contains
        the list of previous sale orders (state in sale/done) for the
        current order.partner_id and this product."""
        # Works for single-line click in the order_line tree; support multiple just in case:
        self.ensure_one()
        if not self.product_id:
            return {}

        partner = self.order_id.partner_id
        # search sale orders of this partner in confirmed/done states
        orders = self.env['sale.order'].search([
            ('partner_id', '=', partner.id),
            ('state', 'in', ('sale', 'done'))
        ])

        values = []
        # Build lines for transient model (product.sale.history.line)
        for order in orders:
            for line in order.order_line:
                if line.product_id.id == self.product_id.id:
                    values.append((0, 0, {
                        'sale_order_id': order.id,
                        'history_price': line.price_unit,
                        'history_qty': line.product_uom_qty,
                        'history_total': order.amount_total,
                    }))

        # create transient wizard record
        history = self.env['product.sale.order.history'].create({
            'product_id': self.product_id.id,
            'product_sale_history_ids': values,
        })

        return {
            'name': 'Customer Product Sales History',
            'type': 'ir.actions.act_window',
            'res_model': 'product.sale.order.history',
            'view_mode': 'form',
            'res_id': history.id,
            'target': 'new',
        }

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
from odoo import fields, models


class ProductSaleOrderHistory(models.TransientModel):
    _name = 'product.sale.order.history'
    _description = 'Product Sale Order History'
    _rec_name = 'product_id'

    product_id = fields.Many2one(
        'product.product',
        string="Product",
        help="Product for which history is shown",
        readonly=True
    )
    product_sale_history_ids = fields.One2many(
        'product.sale.history.line',
        'history_id',  # ✅ was 'order_line_id', now correct
        string='Product Sale Price History',
        help="Shows the product sale history lines for the selected product",
        readonly=True
    )

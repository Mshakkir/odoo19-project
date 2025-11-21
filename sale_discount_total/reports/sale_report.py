# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Sreerag PM(odoo@cybrosys.com)
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
#############################################################################
from odoo import fields, models
from odoo.tools import SQL


class DiscountSaleReport(models.Model):
    """This class inherits 'sale.report' and adds field discount"""
    _inherit = 'sale.report'

    discount = fields.Float(
        string='Discount',
        readonly=True,
        help="Specify the discount amount.")

    def _select(self) -> SQL:
        """Extend the select query to include discount calculation.
        This calculates the total discount for sales transactions based on
        quantity, unit price, and discount percentage."""
        return SQL(
            "%s, SUM(l.product_uom_qty / NULLIF(u.factor, 0) * u2.factor * "
            "COALESCE(cr.rate, 1.0) * l.price_unit * l.discount / 100.0) AS discount",
            super()._select()
        )
# Copyright 2017 ForgeFlow S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

from odoo import fields, models


class SaleOrderTemplateLine(models.Model):
    _inherit = "sale.order.template.line"

    discount_fixed = fields.Monetary(
        string="Discount (Fixed)",
        default=0.0,
        help=(
            "Apply a fixed total discount to this line. "
            "This is a total discount amount, not per unit."
        ),
    )
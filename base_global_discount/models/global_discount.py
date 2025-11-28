# Copyright 2019 Tecnativa - David Vidal
# Copyright 2025 - Odoo 19 CE Conversion
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class GlobalDiscount(models.Model):
    _name = "global.discount"
    _description = "Global Discount"
    _order = "sequence, id desc"

    sequence = fields.Integer(
        string="Sequence",
        default=10,
        help="Gives the order to apply discounts. Lower values are applied first.",
    )
    name = fields.Char(
        string="Discount Name",
        required=True,
        translate=True,
    )
    discount = fields.Float(
        string="Discount (%)",
        digits="Discount",
        required=True,
        default=0.0,
    )
    discount_scope = fields.Selection(
        selection=[
            ("sale", "Sales"),
            ("purchase", "Purchases"),
        ],
        string="Scope",
        default="sale",
        required=True,
        help="Determines where this discount will be applied",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
        help="Leave empty to make this discount available in all companies",
    )
    active = fields.Boolean(
        default=True,
        help="If unchecked, it will allow you to hide the discount without removing it.",
    )

    @api.depends("name", "discount")
    def _compute_display_name(self):
        """Compute display name with discount percentage."""
        for one in self:
            one.display_name = f"{one.name} ({one.discount:.2f}%)"

    def _get_global_discount_vals(self, base, **kwargs):
        """Prepare the dict of values to create to obtain the discounted amount."""
        self.ensure_one()
        return {
            "global_discount": self,
            "base": base,
            "base_discounted": base * (1 - (self.discount / 100)),
        }
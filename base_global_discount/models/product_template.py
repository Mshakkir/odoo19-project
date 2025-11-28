# Copyright 2024 Studio73 - Ferran Mora
# Copyright 2025 - Odoo 19 CE Conversion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    bypass_global_discount = fields.Boolean(
        string="Don't apply global discount",
        help=(
            "If this checkbox is ticked, it means that this product will not be "
            "taken into account when calculating the global discounts."
        ),
        compute="_compute_bypass_global_discount",
        inverse="_inverse_bypass_global_discount",
        search="_search_bypass_global_discount",
        store=False,
    )

    def _search_bypass_global_discount(self, operator, value):
        """Search method for bypass_global_discount field."""
        templates = self.with_context(active_test=False).search(
            [("product_variant_ids.bypass_global_discount", operator, value)]
        )
        return [("id", "in", templates.ids)]

    @api.depends("product_variant_ids.bypass_global_discount")
    def _compute_bypass_global_discount(self):
        """Compute bypass_global_discount from variants."""
        for template in self:
            if len(template.product_variant_ids) == 1:
                template.bypass_global_discount = (
                    template.product_variant_ids.bypass_global_discount
                )
            else:
                template.bypass_global_discount = False

    def _inverse_bypass_global_discount(self):
        """Inverse method to set bypass on variant."""
        for template in self:
            if len(template.product_variant_ids) == 1:
                template.product_variant_ids.bypass_global_discount = (
                    template.bypass_global_discount
                )
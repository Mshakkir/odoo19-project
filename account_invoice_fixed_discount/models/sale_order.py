# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    global_discount_fixed = fields.Monetary(
        string="Global Discount (Fixed)",
        default=0.0,
        currency_field="currency_id",
    )

    @api.onchange('global_discount_fixed')
    def _onchange_global_discount_fixed(self):
        """Remove old discount line and create a new one with correct tax logic."""
        # Remove existing global discount lines
        self.order_line = self.order_line.filtered(lambda l: not l.is_global_discount)

        if self.global_discount_fixed > 0:
            # Collect taxes from normal lines
            tax_ids = []
            for line in self.order_line:
                if not line.is_global_discount:
                    for t in line.tax_id:
                        if t.id not in tax_ids:
                            tax_ids.append(t.id)

            # Create new discount line
            self.order_line.create({
                'order_id': self.id,
                'name': "Global Discount",
                'product_uom_qty': 1,
                'price_unit': -abs(self.global_discount_fixed),
                'is_global_discount': True,
                'tax_id': [(6, 0, tax_ids)],   # VERY IMPORTANT
            })


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    is_global_discount = fields.Boolean(string="Global Discount Line", default=False)

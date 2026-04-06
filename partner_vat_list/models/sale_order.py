# -*- coding: utf-8 -*-
from odoo import models, api


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.onchange('product_id')
    def _onchange_product_id_partner_vat(self):
        """
        After the standard product_id onchange, override tax_id
        with the partner's VAT list rule if one exists.
        """
        order = self.order_id
        if not order:
            return

        partner = order.partner_id
        if not partner or not partner.vat_line_ids:
            return

        product = self.product_id
        if not product:
            return

        partner_tax = partner.get_partner_tax_for_product(product, 'sale')
        if partner_tax:
            self.tax_id = [(6, 0, [partner_tax.id])]

    # ------------------------------------------------------------------ #
    #  Also handle programmatic writes (e.g. import / API calls)          #
    # ------------------------------------------------------------------ #
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._apply_partner_vat()
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'product_id' in vals or 'order_id' in vals:
            self._apply_partner_vat()
        return res

    def _apply_partner_vat(self):
        for line in self:
            partner = line.order_id.partner_id
            if not partner or not partner.vat_line_ids or not line.product_id:
                continue
            partner_tax = partner.get_partner_tax_for_product(
                line.product_id, 'sale'
            )
            if partner_tax:
                line.tax_id = [(6, 0, [partner_tax.id])]

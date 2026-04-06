# -*- coding: utf-8 -*-
from odoo import models, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.onchange('product_id')
    def _onchange_product_id_partner_vat(self):
        """
        After the standard product_id onchange runs, override the tax_ids
        with the partner's configured VAT list (if any matching rule exists).
        """
        move = self.move_id
        if not move:
            return

        partner = move.partner_id
        if not partner or not partner.vat_line_ids:
            return

        product = self.product_id
        if not product:
            return

        # Determine tax direction based on move type
        if move.move_type in ('out_invoice', 'out_refund'):
            tax_type = 'sale'
        elif move.move_type in ('in_invoice', 'in_refund'):
            tax_type = 'purchase'
        else:
            return

        partner_tax = partner.get_partner_tax_for_product(product, tax_type)
        if partner_tax:
            self.tax_ids = [(6, 0, [partner_tax.id])]


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_tax_for_line(self, product, partner, tax_type):
        """
        Utility used by other models to get the right tax.
        Returns account.tax or empty recordset.
        """
        if partner and partner.vat_line_ids and product:
            return partner.get_partner_tax_for_product(product, tax_type)
        return self.env['account.tax']

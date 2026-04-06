# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    vat_line_ids = fields.One2many(
        'partner.vat.line',
        'partner_id',
        string='VAT / Tax List',
        help='Define specific taxes for this partner. '
             'These taxes will be automatically applied when this partner '
             'is selected on Sale Orders, Purchase Orders, and Invoices.',
    )

    # Quick summary fields for the form view
    vat_line_count = fields.Integer(
        compute='_compute_vat_line_count',
        string='VAT Rules Count',
    )

    @api.depends('vat_line_ids')
    def _compute_vat_line_count(self):
        for partner in self:
            partner.vat_line_count = len(partner.vat_line_ids)

    def get_partner_tax_for_product(self, product, tax_type='sale'):
        """
        Core helper: Given a product and tax_type ('sale' or 'purchase'),
        return the matching account.tax record from this partner's VAT list.

        Priority order:
          1. Exact product match (product.product)
          2. Product category match
          3. Generic rule (no product / category scope)
          4. None (fall back to Odoo default behaviour)

        :param product: product.product recordset (single record)
        :param tax_type: 'sale' or 'purchase'
        :return: account.tax recordset (may be empty)
        """
        self.ensure_one()
        if not self.vat_line_ids:
            return self.env['account.tax']

        active_lines = self.vat_line_ids.filtered(
            lambda l: l.tax_type == tax_type and l.active
        )

        # 1. Exact product variant match
        if product:
            product_match = active_lines.filtered(
                lambda l: l.product_id and l.product_id.id == product.id
            )
            if product_match:
                return product_match[0].tax_id

            # 2. Product category match (walk up the category tree)
            category = product.categ_id
            while category:
                cat_match = active_lines.filtered(
                    lambda l, c=category: l.product_category_id
                    and l.product_category_id.id == c.id
                    and not l.product_id
                )
                if cat_match:
                    return cat_match[0].tax_id
                category = category.parent_id

        # 3. Generic fallback — lines with no product and no category scope
        generic = active_lines.filtered(
            lambda l: not l.product_id and not l.product_category_id
        )
        if generic:
            return generic[0].tax_id

        return self.env['account.tax']

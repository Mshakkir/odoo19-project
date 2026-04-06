# -*- coding: utf-8 -*-
from odoo import models, fields, api


class PartnerVatLine(models.Model):
    """
    Stores VAT/Tax lines assigned to a partner.
    Each line maps:
      - A tax (account.tax)
      - Optionally scoped to a product category or specific product
      - A type: 'sale' (customer tax) or 'purchase' (vendor tax)
    When no product/category scope is set, the tax applies to ALL products
    for this partner.
    """
    _name = 'partner.vat.line'
    _description = 'Partner VAT / Tax Line'
    _order = 'sequence, id'

    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        required=True,
        ondelete='cascade',
        index=True,
    )
    sequence = fields.Integer(string='Sequence', default=10)
    tax_id = fields.Many2one(
        'account.tax',
        string='Tax / VAT',
        required=True,
        domain="[('type_tax_use', '=', tax_type)]",
    )
    tax_type = fields.Selection(
        selection=[('sale', 'Sales Tax'), ('purchase', 'Purchase Tax')],
        string='Tax Type',
        required=True,
        default='sale',
    )
    # Optional scoping — if blank, applies to all products
    product_id = fields.Many2one(
        'product.product',
        string='Specific Product',
        help='Leave blank to apply to all products. '
             'If set, this tax is used only for this specific product variant.',
    )
    product_category_id = fields.Many2one(
        'product.category',
        string='Product Category',
        help='Leave blank to apply to all categories. '
             'If set, this tax is used for any product in this category.',
    )
    tax_name = fields.Char(related='tax_id.name', string='Tax Name', store=True)
    tax_amount = fields.Float(related='tax_id.amount', string='Tax %', store=True)
    active = fields.Boolean(default=True)

    @api.constrains('product_id', 'product_category_id', 'tax_type', 'partner_id')
    def _check_uniqueness(self):
        """Warn if duplicate scope exists (same partner+product+type)."""
        for rec in self:
            if rec.product_id:
                duplicates = self.search([
                    ('partner_id', '=', rec.partner_id.id),
                    ('product_id', '=', rec.product_id.id),
                    ('tax_type', '=', rec.tax_type),
                    ('id', '!=', rec.id),
                ])
                if duplicates:
                    from odoo.exceptions import ValidationError
                    raise ValidationError(
                        f"A {rec.tax_type} tax rule for product '{rec.product_id.name}' "
                        f"already exists on this partner. Remove the duplicate."
                    )

# Copyright 2019 Tecnativa - David Vidal
# Copyright 2025 - Odoo 19 CE Conversion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    customer_global_discount_ids = fields.Many2many(
        comodel_name="global.discount",
        relation="customer_global_discount_rel",
        column1="partner_id",
        column2="global_discount_id",
        string="Sale Global Discounts",
        domain="[('discount_scope', '=', 'sale'), '|', "
        "('company_id', '=', False), ('company_id', '=', company_id)]",
        help="Global discounts applied to customer invoices for this partner",
    )
    supplier_global_discount_ids = fields.Many2many(
        comodel_name="global.discount",
        relation="supplier_global_discount_rel",
        column1="partner_id",
        column2="global_discount_id",
        string="Purchase Global Discounts",
        domain="[('discount_scope', '=', 'purchase'), '|', "
        "('company_id', '=', False), ('company_id', '=', company_id)]",
        help="Global discounts applied to vendor bills for this partner",
    )
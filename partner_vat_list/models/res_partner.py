from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # ─── Sales VAT List ───────────────────────────────────────────────────────
    sale_tax_ids = fields.Many2many(
        comodel_name='account.tax',
        relation='res_partner_sale_tax_rel',
        column1='partner_id',
        column2='tax_id',
        string='Sales VAT List',
        domain="[('type_tax_use', 'in', ('sale', 'all')), ('company_id', '=', company_id)]",
        help='Default VAT taxes to apply automatically on Sales Order and Customer Invoice lines '
             'when this partner is selected as customer.',
    )

    # ─── Purchase VAT List ────────────────────────────────────────────────────
    purchase_tax_ids = fields.Many2many(
        comodel_name='account.tax',
        relation='res_partner_purchase_tax_rel',
        column1='partner_id',
        column2='tax_id',
        string='Purchase VAT List',
        domain="[('type_tax_use', 'in', ('purchase', 'all')), ('company_id', '=', company_id)]",
        help='Default VAT taxes to apply automatically on Purchase Order and Vendor Bill lines '
             'when this partner is selected as vendor.',
    )

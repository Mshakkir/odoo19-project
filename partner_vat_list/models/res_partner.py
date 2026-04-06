from odoo import api, fields, models


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

    # ─── Sales Currency ───────────────────────────────────────────────────────
    sale_currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Sales Currency',
        store=True,
        copy=True,
        help='Default currency to apply on new Sale Orders for this customer.',
    )

    # ─── Currency Rate fields (mirrors sale_order.py logic) ──────────────────
    manual_currency_rate = fields.Float(
        string='Currency Rate',
        digits=(12, 6),
        store=True,
        copy=False,
        help='Default exchange rate: how many company currency units = 1 sale currency unit. '
             'This will be copied to new Sale Orders for this customer.',
    )

    company_currency_id = fields.Many2one(
        related='company_id.currency_id',
        string='Company Currency',
        store=False,
        readonly=True,
    )

    currency_rate_prefix = fields.Char(
        compute='_compute_currency_rate_affixes',
        store=False,
    )
    currency_rate_suffix = fields.Char(
        compute='_compute_currency_rate_affixes',
        store=False,
    )

    # ─── Compute prefix/suffix labels (e.g. "1 USD =" / "SAR") ──────────────
    @api.depends('sale_currency_id', 'company_id')
    def _compute_currency_rate_affixes(self):
        for partner in self:
            company_currency = partner.company_id.currency_id
            sale_currency = partner.sale_currency_id
            if sale_currency and company_currency and sale_currency != company_currency:
                partner.currency_rate_prefix = "1 %s =" % sale_currency.name
                partner.currency_rate_suffix = company_currency.name
            else:
                partner.currency_rate_prefix = ""
                partner.currency_rate_suffix = ""

    # ─── Auto-fill rate when currency changes ────────────────────────────────
    @api.onchange('sale_currency_id')
    def _onchange_sale_currency_auto_fill_rate(self):
        for partner in self:
            company_currency = partner.company_id.currency_id
            sale_currency = partner.sale_currency_id
            if sale_currency and company_currency and sale_currency != company_currency:
                rate_date = fields.Date.today()
                rate_record = self.env['res.currency.rate'].search([
                    ('currency_id', '=', sale_currency.id),
                    ('company_id', '=', (partner.company_id.id or self.env.company.id)),
                    ('name', '<=', str(rate_date)),
                ], order='name desc', limit=1)
                if rate_record and rate_record.inverse_company_rate:
                    partner.manual_currency_rate = rate_record.inverse_company_rate
                else:
                    partner.manual_currency_rate = 0.0
            else:
                partner.manual_currency_rate = 0.0
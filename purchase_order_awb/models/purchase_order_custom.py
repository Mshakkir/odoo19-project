from odoo import models, fields, api
import copy


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    awb_number = fields.Char(
        string='Shipping Ref #',
        help='Air Waybill Number for tracking shipment',
        copy=False,
        readonly=False
    )

    delivery_address_id = fields.Many2one(
        'res.partner',
        string='Delivery Address',
        help='Delivery address for this purchase order',
        copy=True,
    )

    manual_currency_rate = fields.Float(
        string='Currency Rate',
        digits=(12, 6),
        store=True,
        copy=False,
        help='Exchange rate: how many SAR = 1 order currency.',
    )

    currency_rate_prefix = fields.Char(
        compute='_compute_currency_rate_affixes',
        store=False,
    )
    currency_rate_suffix = fields.Char(
        compute='_compute_currency_rate_affixes',
        store=False,
    )

    company_currency_id = fields.Many2one(
        related='company_id.currency_id',
        string='Company Currency',
        store=False,
        readonly=True,
    )

    amount_total_company_currency = fields.Monetary(
        string='Total in Company Currency',
        compute='_compute_amount_total_company_currency',
        store=True,
        currency_field='company_currency_id',
    )

    @api.depends('currency_id', 'company_id')
    def _compute_currency_rate_affixes(self):
        for order in self:
            company_currency = order.company_id.currency_id
            order_currency = order.currency_id
            if order_currency and company_currency and order_currency != company_currency:
                order.currency_rate_prefix = "1 %s =" % order_currency.name
                order.currency_rate_suffix = company_currency.name
            else:
                order.currency_rate_prefix = ""
                order.currency_rate_suffix = ""

    @api.depends('amount_total', 'manual_currency_rate', 'currency_id', 'company_id')
    def _compute_amount_total_company_currency(self):
        for order in self:
            company_currency = order.company_id.currency_id
            order_currency = order.currency_id
            if order_currency and company_currency and order_currency != company_currency:
                rate = order.manual_currency_rate
                if not rate:
                    rate_date = order.date_order.date() if order.date_order else fields.Date.today()
                    rate = order._get_system_rate(order_currency, order.company_id.id, rate_date)
                order.amount_total_company_currency = order.amount_total * rate
            else:
                order.amount_total_company_currency = order.amount_total

    def _get_system_rate(self, order_currency, company_id, rate_date):
        rate_record = self.env['res.currency.rate'].search([
            ('currency_id', '=', order_currency.id),
            ('company_id', '=', company_id),
            ('name', '<=', str(rate_date)),
        ], order='name desc', limit=1)
        if rate_record and rate_record.inverse_company_rate:
            return rate_record.inverse_company_rate
        rate = order_currency._get_rates(
            self.env['res.company'].browse(company_id), rate_date
        )
        unit_per_sar = rate.get(order_currency.id, 1.0)
        return (1.0 / unit_per_sar) if unit_per_sar else 1.0

    @api.onchange('currency_id', 'date_order')
    def _onchange_currency_auto_fill_rate(self):
        for order in self:
            company_currency = order.company_id.currency_id
            order_currency = order.currency_id
            if order_currency and company_currency and order_currency != company_currency:
                rate_date = order.date_order.date() if order.date_order else fields.Date.today()
                order.manual_currency_rate = self._get_system_rate(
                    order_currency, order.company_id.id, rate_date
                )
            else:
                order.manual_currency_rate = 1.0

    def _compute_tax_totals(self):
        """
        Override to remove company currency conversion data from
        the tax_totals JSON so the JS widget does NOT render the
        built-in (1,875.00 SR) line. We show our own field instead.
        """
        super()._compute_tax_totals()
        for order in self:
            if order.tax_totals and isinstance(order.tax_totals, dict):
                # Make a mutable copy and strip company currency keys
                totals = copy.deepcopy(order.tax_totals)
                totals.pop('company_currency_id', None)
                totals.pop('amount_total_company_currency', None)
                totals.pop('amount_untaxed_company_currency', None)
                # Reassign to trigger field update
                order.tax_totals = totals

    def _get_own_company_partner_id(self):
        return self.env.company.partner_id.id







# from odoo import models, fields, api
#
# class PurchaseOrder(models.Model):
#     _inherit = 'purchase.order'
#
#     awb_number = fields.Char(
#         string='Shipping Ref #',
#         help='Air Waybill Number for tracking shipment',
#         copy=False,
#         readonly=False
#     )
#
#     delivery_address_id = fields.Many2one(
#         'res.partner',
#         string='Delivery Address',
#         help='Delivery address for this purchase order',
#         copy=True,
#     )
#
#     def _get_own_company_partner_id(self):
#         return self.env.company.partner_id.id

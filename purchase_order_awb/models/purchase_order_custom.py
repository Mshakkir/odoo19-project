from odoo import models, fields, api

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

    # -------------------------------------------------------
    # Currency rate display: "1 USD = 3.750000 SAR"
    # Shows how many company currency units = 1 order currency
    # -------------------------------------------------------
    currency_rate_label = fields.Char(
        string='Currency Rate',
        compute='_compute_currency_rate_label',
        store=False,
        help='Exchange rate: 1 [order currency] = X [company currency]'
    )

    currency_rate_display = fields.Float(
        string='Currency Rate Value',
        compute='_compute_currency_rate_label',
        store=False,
        digits=(12, 6),
    )

    @api.depends('currency_id', 'company_id', 'date_order')
    def _compute_currency_rate_label(self):
        """
        Compute rate as: 1 [order currency] = X [company currency]
        Example: 1 USD = 3.750000 SAR
        Uses inverse_company_rate from res.currency.rate
        """
        for order in self:
            company_currency = order.company_id.currency_id
            order_currency = order.currency_id
            if order_currency and company_currency and order_currency != company_currency:
                rate_date = order.date_order.date() if order.date_order else fields.Date.today()
                # Find most recent rate on or before rate_date
                rate_record = self.env['res.currency.rate'].search([
                    ('currency_id', '=', order_currency.id),
                    ('company_id', '=', order.company_id.id),
                    ('name', '<=', str(rate_date)),
                ], order='name desc', limit=1)

                if rate_record and rate_record.inverse_company_rate:
                    sar_per_unit = rate_record.inverse_company_rate
                else:
                    # Fallback: compute from currency rate
                    rate = order_currency._get_rates(order.company_id, rate_date)
                    unit_per_sar = rate.get(order_currency.id, 1.0)
                    sar_per_unit = (1.0 / unit_per_sar) if unit_per_sar else 1.0

                order.currency_rate_display = sar_per_unit
                order.currency_rate_label = "1 %s = %.6f %s" % (
                    order_currency.name,
                    sar_per_unit,
                    company_currency.name,
                )
            else:
                order.currency_rate_display = 1.0
                order.currency_rate_label = ""

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

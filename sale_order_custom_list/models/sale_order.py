# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    date_order_formatted = fields.Char(
        string='Order Date',
        compute='_compute_sale_formatted_dates',
        store=False,
    )

    validity_date_formatted = fields.Char(
        string='Expiration',
        compute='_compute_sale_formatted_dates',
        store=False,
    )

    commitment_date_formatted = fields.Char(
        string='Delivery Date',
        compute='_compute_sale_formatted_dates',
        store=False,
    )

    @api.depends('date_order', 'validity_date', 'commitment_date')
    def _compute_sale_formatted_dates(self):
        for order in self:
            order.date_order_formatted = (
                order.date_order.strftime('%d/%m/%Y')
                if order.date_order else ''
            )
            order.validity_date_formatted = (
                order.validity_date.strftime('%d/%m/%Y')
                if order.validity_date else ''
            )
            order.commitment_date_formatted = (
                order.commitment_date.strftime('%d/%m/%Y')
                if order.commitment_date else ''
            )

    # ── Company Currency Amount Fields ───────────────────────────────────────
    company_currency_id = fields.Many2one(
        related='company_id.currency_id',
        string='Company Currency',
        store=False,
        readonly=True,
    )

    amount_untaxed_company_currency = fields.Monetary(
        string='Tax Excluded (Company Currency)',
        compute='_compute_sale_amounts_company_currency',
        store=True,
        currency_field='company_currency_id',
    )

    amount_tax_company_currency = fields.Monetary(
        string='Tax (Company Currency)',
        compute='_compute_sale_amounts_company_currency',
        store=True,
        currency_field='company_currency_id',
    )

    amount_total_company_currency = fields.Monetary(
        string='Total (Company Currency)',
        compute='_compute_sale_amounts_company_currency',
        store=True,
        currency_field='company_currency_id',
    )

    @api.depends(
        'amount_untaxed', 'amount_tax', 'amount_total',
        'manual_currency_rate', 'currency_id', 'company_id'
    )
    def _compute_sale_amounts_company_currency(self):
        for order in self:
            company_currency = order.company_id.currency_id
            order_currency = order.currency_id
            if order_currency and company_currency and order_currency != company_currency:
                rate = order.manual_currency_rate
                if not rate:
                    rate_date = order.date_order.date() if order.date_order else fields.Date.today()
                    rate_record = order.env['res.currency.rate'].search([
                        ('currency_id', '=', order_currency.id),
                        ('company_id', '=', order.company_id.id),
                        ('name', '<=', str(rate_date)),
                    ], order='name desc', limit=1)
                    rate = rate_record.inverse_company_rate if rate_record else 1.0
                order.amount_untaxed_company_currency = order.amount_untaxed * rate
                order.amount_tax_company_currency = order.amount_tax * rate
                order.amount_total_company_currency = order.amount_total * rate
            else:
                order.amount_untaxed_company_currency = order.amount_untaxed
                order.amount_tax_company_currency = order.amount_tax
                order.amount_total_company_currency = order.amount_total








# # -*- coding: utf-8 -*-
# from odoo import models, fields, api
#
#
# class SaleOrder(models.Model):
#     _inherit = 'sale.order'
#
#     date_order_formatted = fields.Char(
#         string='Order Date',
#         compute='_compute_sale_formatted_dates',
#         store=False,
#     )
#
#     validity_date_formatted = fields.Char(
#         string='Expiration',
#         compute='_compute_sale_formatted_dates',
#         store=False,
#     )
#
#     commitment_date_formatted = fields.Char(
#         string='Delivery Date',
#         compute='_compute_sale_formatted_dates',
#         store=False,
#     )
#
#     @api.depends('date_order', 'validity_date', 'commitment_date')
#     def _compute_sale_formatted_dates(self):
#         for order in self:
#             order.date_order_formatted = (
#                 order.date_order.strftime('%d/%m/%Y')
#                 if order.date_order else ''
#             )
#             order.validity_date_formatted = (
#                 order.validity_date.strftime('%d/%m/%Y')
#                 if order.validity_date else ''
#             )
#             order.commitment_date_formatted = (
#                 order.commitment_date.strftime('%d/%m/%Y')
#                 if order.commitment_date else ''
#             )
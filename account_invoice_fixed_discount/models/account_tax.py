# Copyright 2017 ForgeFlow S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

from odoo import api, models
from odoo.tools.float_utils import float_is_zero


class AccountTax(models.Model):
    _inherit = "account.tax"

    @api.model
    def _prepare_base_line_for_taxes_computation(self, record, **kwargs):
        res = super()._prepare_base_line_for_taxes_computation(record, **kwargs)

        if not record:
            return res

        # For Sale Order Lines
        if record._name == "sale.order.line":
            if hasattr(record, 'discount_fixed') and record.discount_fixed:
                currency = record.currency_id or record.order_id.currency_id or record.company_id.currency_id
                rounding = currency.rounding if currency else 0.01

                if not float_is_zero(record.discount_fixed, precision_rounding=rounding):
                    # Calculate equivalent percentage discount
                    subtotal = record.product_uom_qty * record.price_unit
                    if not float_is_zero(subtotal, precision_rounding=rounding):
                        calculated_discount = (record.discount_fixed / subtotal) * 100
                        res["discount"] = calculated_discount

        # For Account Move Lines (Invoices)
        elif record._name == "account.move.line":
            if hasattr(record, 'discount_fixed') and record.discount_fixed:
                currency = record.currency_id or record.company_id.currency_id
                rounding = currency.rounding if currency else 0.01

                if not float_is_zero(record.discount_fixed, precision_rounding=rounding):
                    # Calculate equivalent percentage discount
                    subtotal = record.quantity * record.price_unit
                    if not float_is_zero(subtotal, precision_rounding=rounding):
                        calculated_discount = (record.discount_fixed / subtotal) * 100
                        res["discount"] = calculated_discount

        return res
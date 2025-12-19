# Copyright 2017 ForgeFlow S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

from odoo import api, models
from odoo.tools.float_utils import float_is_zero


class AccountTax(models.Model):
    _inherit = "account.tax"

    @api.model
    def _prepare_base_line_for_taxes_computation(self, record, **kwargs):
        res = super()._prepare_base_line_for_taxes_computation(record, **kwargs)

        if record and record._name == "sale.order.line" and record.discount_fixed:
            currency = record.currency_id or record.order_id.currency_id or record.company_id.currency_id

            # Check if discount_fixed is not zero
            if not float_is_zero(record.discount_fixed, precision_rounding=currency.rounding if currency else 0.01):
                calculated_discount = record._get_discount_from_fixed_discount()
                res["discount"] = calculated_discount

        elif record and record._name == "account.move.line" and record.discount_fixed:
            currency = record.currency_id or record.company_id.currency_id

            # Check if discount_fixed is not zero
            if not float_is_zero(record.discount_fixed, precision_rounding=currency.rounding if currency else 0.01):
                calculated_discount = record._get_discount_from_fixed_discount()
                res["discount"] = calculated_discount

        return res

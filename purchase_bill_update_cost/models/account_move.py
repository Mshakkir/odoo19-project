# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        """
        Override action_post to update product cost price
        when a vendor bill is confirmed/posted.
        """
        res = super().action_post()

        # Only process vendor bills (in_invoice)
        vendor_bills = self.filtered(lambda m: m.move_type == 'in_invoice')

        if vendor_bills:
            # Check if the feature is enabled in settings
            update_cost_enabled = self.env['ir.config_parameter'].sudo().get_param(
                'purchase_bill_update_cost.auto_update_cost', default='True'
            )
            if update_cost_enabled == 'True':
                for bill in vendor_bills:
                    bill._update_product_cost_from_bill()

        return res

    def _update_product_cost_from_bill(self):
        """
        Update the standard price (cost) of products based on
        the unit price in vendor bill lines.
        """
        self.ensure_one()

        for line in self.invoice_line_ids:
            product = line.product_id

            # Skip lines without a product or with zero/negative price
            if not product or line.price_unit <= 0:
                continue

            # Only update for storable products and consumables (not services)
            # Remove this filter if you also want to update service products
            if product.type not in ('consu', 'product'):
                continue

            # Convert the price to company currency if bill is in a different currency
            unit_price_in_company_currency = self._convert_to_company_currency(
                line.price_unit,
                self.currency_id,
                self.company_id,
                self.invoice_date or fields.Date.today(),
            )

            # Get the product template (cost is on product.template)
            product_tmpl = product.product_tmpl_id
            old_cost = product_tmpl.standard_price

            # Only update if price has changed
            if old_cost == unit_price_in_company_currency:
                continue

            # Update the standard price
            # Using sudo() to bypass potential access rights on product write
            product_tmpl.sudo().write({
                'standard_price': unit_price_in_company_currency,
            })

            # Log a message on the product for traceability
            product_tmpl.sudo().message_post(
                body=_(
                    "Cost price updated from vendor bill <b>%(bill)s</b> (Vendor: %(vendor)s).<br/>"
                    "Previous cost: <b>%(old_cost)s %(currency)s</b> → "
                    "New cost: <b>%(new_cost)s %(currency)s</b>",
                    bill=self.name,
                    vendor=self.partner_id.name,
                    old_cost=old_cost,
                    new_cost=unit_price_in_company_currency,
                    currency=self.company_id.currency_id.name,
                ),
            )

            _logger.info(
                "Product cost updated | Product: %s | Bill: %s | "
                "Old Cost: %s | New Cost: %s | Currency: %s",
                product.name,
                self.name,
                old_cost,
                unit_price_in_company_currency,
                self.company_id.currency_id.name,
            )

    def _convert_to_company_currency(self, amount, from_currency, company, date):
        """
        Convert an amount from bill currency to company currency.
        Returns the original amount if currencies are the same.
        """
        company_currency = company.currency_id

        if from_currency == company_currency:
            return amount

        return from_currency._convert(
            amount,
            company_currency,
            company,
            date,
        )
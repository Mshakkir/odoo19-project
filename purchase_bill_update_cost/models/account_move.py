# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.tools import float_compare
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
        Uses manual_currency_rate from purchase_bill_form_modified if set,
        otherwise falls back to Odoo system rate.
        """
        self.ensure_one()

        company_currency = self.company_id.currency_id
        invoice_currency = self.currency_id
        rate_date = self.invoice_date or fields.Date.today()

        # Determine conversion rate once for all lines on this bill:
        # Priority 1 — manual_currency_rate from purchase_bill_form_modified
        # Priority 2 — Odoo system rate
        manual_rate = getattr(self, 'manual_currency_rate', 0.0)
        is_foreign = invoice_currency and invoice_currency != company_currency

        for line in self.invoice_line_ids:
            product = line.product_id

            # Skip lines without a product or with zero/negative price
            if not product or line.price_unit <= 0:
                continue

            # Only update for storable products and consumables (not services)
            if product.type not in ('consu', 'product'):
                continue

            # Convert unit price to company currency
            unit_price_in_company_currency = self._cost_convert_to_company_currency(
                amount=line.price_unit,
                from_currency=invoice_currency,
                company=self.company_id,
                date=rate_date,
                manual_rate=manual_rate if is_foreign else 0.0,
            )

            # Get the product template (cost is on product.template)
            product_tmpl = product.product_tmpl_id
            old_cost = product_tmpl.standard_price

            # Only update if price has actually changed
            if float_compare(old_cost, unit_price_in_company_currency, precision_digits=6) == 0:
                continue

            # Update the standard price
            product_tmpl.sudo().write({
                'standard_price': unit_price_in_company_currency,
            })

            # Build chatter log with currency info
            if is_foreign and manual_rate:
                rate_info = "Rate: 1 %s = %s %s" % (
                    invoice_currency.name,
                    manual_rate,
                    company_currency.name,
                )
                original_price = "%s %s" % (line.price_unit, invoice_currency.name)
            elif is_foreign:
                rate_info = "Rate: system rate on %s" % rate_date
                original_price = "%s %s" % (line.price_unit, invoice_currency.name)
            else:
                rate_info = ""
                original_price = ""

            body_parts = [
                "Cost price updated from vendor bill <b>%s</b> (Vendor: %s)." % (
                    self.name, self.partner_id.name),
            ]
            if original_price:
                body_parts.append("Unit price on bill: <b>%s</b> → %s" % (
                    original_price, rate_info))
            body_parts.append(
                "Previous cost: <b>%s %s</b> → New cost: <b>%s %s</b>" % (
                    old_cost, company_currency.name,
                    unit_price_in_company_currency, company_currency.name,
                )
            )

            product_tmpl.sudo().message_post(
                body="<br/>".join(body_parts),
            )

            _logger.info(
                "Product cost updated | Product: %s | Bill: %s | "
                "Old Cost: %s | New Cost: %s %s | Manual Rate: %s",
                product.name, self.name,
                old_cost, unit_price_in_company_currency, company_currency.name,
                manual_rate or 'system',
            )

    def _cost_convert_to_company_currency(self, amount, from_currency, company, date, manual_rate=0.0):
        """
        Convert amount from bill currency to company currency.

        Priority:
          1. manual_currency_rate (from purchase_bill_form_modified):
             formula → amount * manual_rate
             e.g. 100 USD * 3.75 = 375 SAR

          2. Odoo system rate fallback:
             uses from_currency._convert()
        """
        company_currency = company.currency_id

        # Same currency — no conversion needed
        if not from_currency or from_currency == company_currency:
            return amount

        # Use manual rate if provided (manual_rate = SAR per 1 unit of invoice currency)
        if manual_rate and manual_rate > 0.0:
            return amount * manual_rate

        # Fallback to Odoo system rate
        return from_currency._convert(
            amount,
            company_currency,
            company,
            date,
        )
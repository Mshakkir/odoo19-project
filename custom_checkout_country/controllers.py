from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo import http
from odoo.http import request


class WebsiteSaleExtended(WebsiteSale):

    def _get_mandatory_fields_billing(self, country_id=False):
        """Keep parent mandatory fields unchanged."""
        return super()._get_mandatory_fields_billing(country_id)

    def _checkout_form_save(self, mode, checkout, all_values):
        """Inject short_address_code before saving the partner."""
        partner_id = super()._checkout_form_save(mode, checkout, all_values)
        short_code = all_values.get("short_address_code", "").strip()
        if partner_id and short_code is not None:
            request.env["res.partner"].sudo().browse(partner_id).write(
                {"short_address_code": short_code}
            )
        return partner_id
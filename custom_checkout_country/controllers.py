from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSaleExtended(WebsiteSale):

    def _get_address_fields(self, partner, mode):
        """Add short_address_code to the list of handled address fields."""
        fields = super()._get_address_fields(partner, mode)
        fields.append("short_address_code")
        return fields

    def _checkout_form_save(self, mode, checkout, all_values):
        """Save short_address_code to partner after standard save."""
        partner_id = super()._checkout_form_save(mode, checkout, all_values)
        short_code = all_values.get("short_address_code", "")
        if partner_id and short_code is not None:
            request.env["res.partner"].sudo().browse(partner_id).write(
                {"short_address_code": short_code}
            )
        return partner_id
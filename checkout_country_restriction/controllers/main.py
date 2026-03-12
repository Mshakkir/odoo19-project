from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSaleExtended(WebsiteSale):

    def _checkout_form_save(self, mode, checkout, all_values):
        """Override to persist short_address_code on the partner record."""
        partner_id = super()._checkout_form_save(mode, checkout, all_values)
        short_code = all_values.get("short_address_code", "")
        if partner_id:
            request.env["res.partner"].sudo().browse(partner_id).write(
                {"short_address_code": short_code}
            )
        return partner_id

from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSaleExtended(WebsiteSale):

    def _get_vat_validation_fields(self, data):
        res = super()._get_vat_validation_fields(data)
        return res

    def _checkout_form_save(self, mode, checkout, all_values):
        """Override to persist short_address_code on the partner record."""
        # short_address_code is NOT in checkout dict (Odoo strips unknown fields)
        # so we grab it from all_values (raw POST) and write it manually after save
        partner_id = super()._checkout_form_save(mode, checkout, all_values)
        short_code = all_values.get('short_address_code', '')
        if partner_id:
            request.env['res.partner'].sudo().browse(partner_id).write({
                'short_address_code': short_code,
            })
        return partner_id
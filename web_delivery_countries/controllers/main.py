# -*- coding: utf-8 -*-
# File: controllers/main.py
from odoo import http
from odoo.http import request
import json


class WebDeliveryCountriesController(http.Controller):

    @http.route('/web_delivery_countries/get_allowed_countries',
                type='json', auth='public', methods=['POST'])
    def get_allowed_countries(self):
        """Return list of countries with active delivery methods"""
        delivery_methods = request.env['delivery.carrier'].sudo().search([
            ('active', '=', True)
        ])

        countries = request.env['res.country'].sudo()
        for method in delivery_methods:
            if method.country_ids:
                countries |= method.country_ids

        return {
            'country_ids': countries.ids,
        }
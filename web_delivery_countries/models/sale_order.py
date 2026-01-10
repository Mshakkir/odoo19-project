from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def get_delivery_countries(self):
        """Get countries from active delivery methods"""
        delivery_methods = self.env['delivery.carrier'].search([
            ('active', '=', True)
        ])

        countries = self.env['res.country']
        for method in delivery_methods:
            if method.country_ids:
                countries |= method.country_ids

        return countries.ids if countries else []

    def _get_country_domain(self):
        """Return domain for country field on checkout"""
        country_ids = self.get_delivery_countries()
        if country_ids:
            return [('id', 'in', country_ids)]
        return []
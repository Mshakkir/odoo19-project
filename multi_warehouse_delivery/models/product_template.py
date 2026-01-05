from odoo import models, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def _get_report_data(self, domain, read_fields):
        """Override to ensure data is properly loaded when switching warehouses"""
        try:
            result = super()._get_report_data(domain, read_fields)

            # Ensure product_templates exists in result
            if result and 'product_templates' not in result:
                result['product_templates'] = []

            return result
        except Exception as e:
            # Fallback to ensure we don't break the view
            return {
                'product_templates': [],
                'lines': [],
            }


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def _get_report_data(self, domain, read_fields):
        """Override to ensure data is properly loaded when switching warehouses"""
        try:
            result = super()._get_report_data(domain, read_fields)

            # Ensure product_templates exists in result
            if result and 'product_templates' not in result:
                result['product_templates'] = []

            return result
        except Exception as e:
            # Fallback to ensure we don't break the view
            return {
                'product_templates': [],
                'lines': [],
            }
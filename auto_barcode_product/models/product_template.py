from odoo import models, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model_create_multi
    def create(self, vals_list):
        """
        Auto-generate a barcode for each new product if barcode is not already set.
        The barcode is generated from the ir.sequence with code 'product.barcode'.
        """
        for vals in vals_list:
            if not vals.get('barcode'):
                vals['barcode'] = self.env['ir.sequence'].next_by_code('product.barcode')
        return super().create(vals_list)
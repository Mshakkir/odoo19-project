from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    x_created_date = fields.Date(
        string='Created Date',
        readonly=True,
        copy=False,
        default=fields.Date.today,
        help='Date when this product was created. Auto-filled on creation.',
    )

    @api.model_create_multi
    def create(self, vals_list):
        today = fields.Date.context_today(self)
        for vals in vals_list:
            if not vals.get('x_created_date'):
                vals['x_created_date'] = today
        return super().create(vals_list)
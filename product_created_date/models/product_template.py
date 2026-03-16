from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    x_created_date = fields.Date(
        string='Created Date (Raw)',
        readonly=True,
        copy=False,
        default=fields.Date.today,
        help='Date when this product was created. Auto-filled on creation.',
    )

    x_created_date_display = fields.Char(
        string='Created Date',
        compute='_compute_created_date_display',
        store=False,
        readonly=True,
        help='Created date formatted as dd/mm/yy, locale-independent.',
    )

    @api.depends('x_created_date')
    def _compute_created_date_display(self):
        for rec in self:
            if rec.x_created_date:
                rec.x_created_date_display = rec.x_created_date.strftime('%d/%m/%y')
            else:
                rec.x_created_date_display = ''

    @api.model_create_multi
    def create(self, vals_list):
        today = fields.Date.context_today(self)
        for vals in vals_list:
            if not vals.get('x_created_date'):
                vals['x_created_date'] = today
        return super().create(vals_list)




# from odoo import models, fields, api
#
#
# class ProductTemplate(models.Model):
#     _inherit = 'product.template'
#
#     x_created_date = fields.Date(
#         string='Created Date',
#         readonly=True,
#         copy=False,
#         default=fields.Date.today,
#         help='Date when this product was created. Auto-filled on creation.',
#     )
#
#     @api.model_create_multi
#     def create(self, vals_list):
#         today = fields.Date.context_today(self)
#         for vals in vals_list:
#             if not vals.get('x_created_date'):
#                 vals['x_created_date'] = today
#         return super().create(vals_list)
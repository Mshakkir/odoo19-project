# from odoo import fields, models
#
#
# class ResConfigSettings(models.TransientModel):
#     _inherit = "res.config.settings"
#
#     anglo_saxon_accounting = fields.Boolean(
#         related="company_id.anglo_saxon_accounting",
#         readonly=False, string="Use anglo-saxon accounting",
#         help="Record the cost of a good as an expense when this good is invoiced to a final customer."
#     )

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # 👇 Add missing field
    customer_credit_limit = fields.Float(
        string="Customer Credit Limit",
        help="Default credit limit for customers. This can be used to restrict sales or invoices beyond the limit."
    )

    anglo_saxon_accounting = fields.Boolean(
        related="company_id.anglo_saxon_accounting",
        readonly=False,
        string="Use anglo-saxon accounting",
        help="Record the cost of a good as an expense when this good is invoiced to a final customer."
    )

from odoo import models, fields

class SaleOrder(models.Model):
    _inherit = "purchase.order"

    delivery_period = fields.Char(
        string="Delivery Period",
        help="Example: 3-4 Weeks, 10 Days, Immediate"
    )

from odoo import models, fields

class SaleOrderLine(models.Model):
    _inherit = "purchase.order.line"

    delivery_period = fields.Char(
        string="Delivery Time",
        help="Example: 2-3 Weeks, 1 Week, Immediate"
    )
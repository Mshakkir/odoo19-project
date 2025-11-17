from odoo import models, fields

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    delivery_time = fields.Char(
        string="Delivery Time",
        help="Example: 2-3 Weeks, 1 Week, Immediate"
    )

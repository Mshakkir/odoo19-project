from odoo import models, fields

class SaleOrderDatePanel(models.TransientModel):
    _name = "sale.order.date.panel"
    _description = "Sales Order Date Filter Panel"

    date_from = fields.Date(string="From Date", required=True)
    date_to = fields.Date(string="To Date", required=True)

    def action_apply(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Sales Orders",
            "res_model": "sale.order",
            "view_mode": "tree,form",
            "domain": [
                ("date_order", ">=", self.date_from),
                ("date_order", "<=", self.date_to),
            ],
            "target": "current",
        }

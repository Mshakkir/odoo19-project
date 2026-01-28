from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # The button is hidden via XML view, so no need to override the action
    # This file is kept for future customizations if needed
    pass
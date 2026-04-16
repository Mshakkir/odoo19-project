# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    auto_update_cost_on_bill = fields.Boolean(
        string='Update Product Cost on Bill Confirmation',
        help=(
            "When enabled, posting a vendor bill will automatically update "
            "the product's cost price (Standard Price) with the unit price "
            "from the bill line."
        ),
        config_parameter='purchase_bill_update_cost.auto_update_cost',
    )

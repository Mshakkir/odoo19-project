from odoo import models, fields


class ResPartner(models.Model):
    _inherit = "res.partner"

    short_address_code = fields.Char(
        string="Short Address Code",
        help="Short address code used during checkout (e.g. Saudi Post short address).",
    )

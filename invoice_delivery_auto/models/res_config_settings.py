
from odoo import models, fields, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    invoice_auto_create_delivery = fields.Boolean(
        string='Auto Create Delivery from Invoice',
        default=True,
        help='Automatically create delivery orders when customer invoice is posted',
    )

    invoice_auto_validate_delivery = fields.Boolean(
        string='Auto Validate Delivery',
        default=False,
        help='Automatically validate delivery orders created from invoices',
    )

    invoice_check_stock_availability = fields.Boolean(
        string='Check Stock Availability',
        default=False,
        help='Prevent posting invoice if insufficient stock is available',
    )


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    invoice_auto_create_delivery = fields.Boolean(
        related='company_id.invoice_auto_create_delivery',
        readonly=False,
        string='Auto Create Delivery from Invoice',
    )

    invoice_auto_validate_delivery = fields.Boolean(
        related='company_id.invoice_auto_validate_delivery',
        readonly=False,
        string='Auto Validate Delivery',
    )

    invoice_check_stock_availability = fields.Boolean(
        related='company_id.invoice_check_stock_availability',
        readonly=False,
        string='Check Stock Availability',
    )
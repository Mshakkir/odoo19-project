from odoo import models, fields, api

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    awb_number = fields.Char(
        string='AWB Number',
        help='Air Waybill Number for tracking shipment',
        copy=False,
        readonly=False
    )
from odoo import models, fields, api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    awb_number = fields.Char(
        string='AWB Number',
        help='Air Waybill Number for tracking shipment',
        copy=False,
        readonly=False
    )

    tracking_status = fields.Selection([
        ('pending', 'Pending'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ], string='Tracking Status', default='pending')

    @api.onchange('awb_number')
    def onchange_awb_number(self):
        """When AWB is entered, auto-update tracking status"""
        if self.awb_number:
            self.tracking_status = 'in_transit'
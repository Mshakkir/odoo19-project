from odoo import models, fields, api

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    awb_number = fields.Char(
        string='Shipping Ref #',
        help='Air Waybill Number for tracking shipment',
        copy=False,
        readonly=False
    )

    delivery_address_id = fields.Many2one(
        'res.partner',
        string='Delivery Address',
        help='Delivery address for this purchase order',
        copy=True,
    )

    def _get_own_company_partner_id(self):
        return self.env.company.partner_id.id

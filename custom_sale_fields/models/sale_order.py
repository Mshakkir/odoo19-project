from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    customer_reference = fields.Char(
        string='PO Number',
        help='Customer reference number or code',
        copy=False
    )

    awb_number = fields.Char(
        string='AWB Number',
        help='Air Waybill Number',
        copy=False
    )

    @api.onchange('partner_id')
    def _onchange_partner_id_custom_fields(self):
        """Auto-populate customer reference if partner has default reference"""
        if self.partner_id and hasattr(self.partner_id, 'ref'):
            self.customer_reference = self.partner_id.ref
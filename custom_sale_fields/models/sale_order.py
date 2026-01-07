from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    customer_reference = fields.Char(
        string='PO Number',
        help='PO number or code',
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

    def _prepare_invoice(self):
        """Override to pass customer reference to invoice"""
        invoice_vals = super()._prepare_invoice()
        if self.customer_reference:
            invoice_vals['customer_reference'] = self.customer_reference
        return invoice_vals
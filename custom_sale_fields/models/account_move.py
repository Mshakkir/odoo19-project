from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    customer_reference = fields.Char(
        string='PO Number',
        help='PO number or code',
        copy=False
    )

    delivery_note_number = fields.Char(
        string='Delivery Note Number',
        help='Delivery note or dispatch number',
        copy=False
    )

    @api.onchange('partner_id')
    def _onchange_partner_id_custom_invoice_fields(self):
        """Auto-populate customer reference if partner has default reference"""
        if self.partner_id and hasattr(self.partner_id, 'ref') and self.move_type in ['out_invoice', 'out_refund']:
            if not self.customer_reference:
                self.customer_reference = self.partner_id.ref
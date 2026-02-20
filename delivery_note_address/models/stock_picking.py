from odoo import models, fields, api

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    partner_shipping_id = fields.Many2one(
        comodel_name='res.partner',
        string='Delivery Address',
        help='The delivery address used for this delivery note.',
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
    )

    @api.onchange('partner_id')
    def _onchange_partner_shipping(self):
        """Auto-fill delivery address from partner if available."""
        if self.partner_id:
            # Use partner's address if it has a child delivery address
            addr = self.partner_id.address_get(['delivery'])
            self.partner_shipping_id = addr.get('delivery', self.partner_id.id)
        else:
            self.partner_shipping_id = False
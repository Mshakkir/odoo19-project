from odoo import models, fields, api

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    partner_shipping_id = fields.Many2one(
        comodel_name='res.partner',
        string='Delivery Address',
        help='The delivery address used for this delivery note.',
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    )

    @api.onchange('partner_id')
    def _onchange_partner_shipping(self):
        if self.partner_id:
            addr = self.partner_id.address_get(['delivery'])
            self.partner_shipping_id = addr.get('delivery', self.partner_id.id)
        else:
            self.partner_shipping_id = False
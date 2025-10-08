from odoo import models, fields, api


class PurchaseHistoryPopupWizard(models.TransientModel):
    _name = 'purchase.history.popup.wizard'
    _description = 'Purchase History Popup Wizard'

    product_id = fields.Many2one('product.product', string="Product", readonly=True)
    history_lines = fields.One2many('purchase.history.popup.line', 'wizard_id', string="History Lines")

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        active_id = self._context.get('active_id')
        if active_id:
            line = self.env['purchase.order.line'].browse(active_id)
            res['product_id'] = line.product_id.id

            # Get purchase history
            order_lines = self.env['purchase.order.line'].search([
                ('product_id', '=', line.product_id.id)
            ], order='date_order desc', limit=10)

            lines = []
            for ol in order_lines:
                lines.append((0, 0, {
                    'order_id': ol.order_id.id,
                    'date_order': ol.order_id.date_order,
                    'partner_id': ol.order_id.partner_id.id,
                    'price_unit': ol.price_unit,
                    'product_qty': ol.product_qty,
                }))
            res['history_lines'] = lines
        return res


class PurchaseHistoryPopupLine(models.TransientModel):
    _name = 'purchase.history.popup.line'
    _description = 'Purchase History Popup Line'

    wizard_id = fields.Many2one('purchase.history.popup.wizard', string="Wizard")
    order_id = fields.Many2one('purchase.order', string="Purchase Order")
    date_order = fields.Datetime(string="Order Date")
    partner_id = fields.Many2one('res.partner', string="Vendor")
    price_unit = fields.Float(string="Unit Price")
    product_qty = fields.Float(string="Quantity")

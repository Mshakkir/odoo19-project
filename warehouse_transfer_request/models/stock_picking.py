from odoo import models, fields, api,


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    transfer_request_id = fields.Many2one(
        'warehouse.transfer.request',
        string='Transfer Request',
        readonly=True
    )

    def button_validate(self):
        """Override to update transfer request state"""
        res = super().button_validate()

        for picking in self:
            if picking.origin:
                # Find related transfer request
                request = self.env['warehouse.transfer.request'].search([
                    ('name', '=', picking.origin)
                ], limit=1)

                if request:
                    # Check if delivery is validated
                    if picking.id == request.delivery_picking_id.id:
                        if picking.state == 'done':
                            request.state = 'in_transit'
                            request.message_post(
                                body=_('Products are in transit to %s.') % request.dest_warehouse_id.name,
                                subject=_('In Transit')
                            )
                            # Notify destination warehouse
                            request._send_notification_email('in_transit')

                    # Check if receipt is validated
                    elif picking.id == request.receipt_picking_id.id:
                        if picking.state == 'done':
                            request.state = 'received'
                            request.message_post(
                                body=_('Products received at %s.') % request.dest_warehouse_id.name,
                                subject=_('Received')
                            )
                            # Notify requester
                            request._send_notification_email('received')

        return res
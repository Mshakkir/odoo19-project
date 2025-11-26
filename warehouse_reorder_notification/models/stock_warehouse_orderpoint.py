from odoo import models, fields, api
from datetime import datetime, timedelta


class StockWarehouseOrderpoint(models.Model):
    _inherit = 'stock.warehouse.orderpoint'

    last_notification_date = fields.Datetime(string='Last Notification Date')

    @api.model
    def _get_reorder_bot_partner(self):
        """Get or create ReorderBot partner"""
        bot_partner = self.env.ref('warehouse_reorder_notification.partner_reorder_bot', raise_if_not_found=False)
        if not bot_partner:
            bot_partner = self.env['res.partner'].sudo().create({
                'name': 'ReorderBot',
                'email': 'reorderbot@yourcompany.com',
                'active': True,
                'is_company': False,
            })
            # Create external ID for the partner
            self.env['ir.model.data'].sudo().create({
                'name': 'partner_reorder_bot',
                'module': 'warehouse_reorder_notification',
                'model': 'res.partner',
                'res_id': bot_partner.id,
            })
        return bot_partner

    # def _send_notification_to_discuss(self, notification_data):
    #     """Send notification message to Discuss"""
    #     # Check if discuss.channel model exists (Odoo 19+)
    #     if 'discuss.channel' in self.env:
    #         DiscussChannel = self.env['discuss.channel']
    #         channel_type_field = 'channel_type'
    #     else:
    #         return  # Skip if discuss module not installed
    #
    #     bot_partner = self._get_reorder_bot_partner()
    #
    #     # Get all active users
    #     all_users = self.env['res.users'].search([('active', '=', True)])
    #
    #     # Filter users who have stock user or manager access
    #     warehouse_users = all_users.filtered(
    #         lambda u: u.has_group('stock.group_stock_user') or u.has_group('stock.group_stock_manager')
    #     )
    #
    #     for user in warehouse_users:
    #         # Check if user has access to this warehouse
    #         if not self._check_user_warehouse_access(user, notification_data['warehouse_id']):
    #             continue
    #
    #         # Find or create direct message channel with user
    #         channel = DiscussChannel.sudo().search([
    #             (channel_type_field, '=', 'chat'),
    #             ('channel_partner_ids', 'in', [user.partner_id.id, bot_partner.id]),
    #         ], limit=1)
    #
    #         if not channel:
    #             channel = DiscussChannel.sudo().create({
    #                 'name': f'ReorderBot, {user.partner_id.name}',
    #                 channel_type_field: 'chat',
    #                 'channel_partner_ids': [(6, 0, [user.partner_id.id, bot_partner.id])],
    #             })
    #
    #         # Format message
    #         message_body = self._format_notification_message(notification_data)
    #
    #         # Post message
    #         channel.sudo().message_post(
    #             body=message_body,
    #             author_id=bot_partner.id,
    #             message_type='comment',
    #             subtype_xmlid='mail.mt_comment',
    #         )
    def _send_notification_to_discuss(self, notification_data):
        """Send alerts to a warehouse-specific channel."""

        DiscussChannel = self.env['discuss.channel']

        warehouse = self.env['stock.warehouse'].browse(notification_data['warehouse_id'])

        # Channel name = per warehouse
        channel_name = f"Reorder Alerts – {warehouse.name}"

        # Try to find existing warehouse channel
        channel = DiscussChannel.sudo().search([
            ('name', '=', channel_name),
            ('channel_type', '=', 'channel'),
        ], limit=1)

        # Create channel if not exist
        if not channel:
            channel = DiscussChannel.sudo().create({
                'name': channel_name,
                'channel_type': 'channel',
            })

        # Collect warehouse users
        all_users = self.env['res.users'].search([('active', '=', True)])

        warehouse_users = all_users.filtered(
            lambda u: (
                              u.has_group('stock.group_stock_user') or
                              u.has_group('stock.group_stock_manager')
                      )
                      and self._check_user_warehouse_access(u, warehouse.id)
        )

        # Add Admin always
        admin_user = self.env.ref("base.user_admin")
        warehouse_users |= admin_user  # include admin

        # Add all allowed users to channel
        for user in warehouse_users:
            channel.write({
                "channel_partner_ids": [(4, user.partner_id.id)]
            })

        # Format alert
        message_body = self._format_notification_message(notification_data)

        # Post message silently (no popup, no OdooBot)
        channel.sudo().message_post(
            body=message_body,
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
            notify=False,
        )

    def _check_user_warehouse_access(self, user, warehouse_id):
        """Check if user has access to warehouse"""
        if user.has_group('stock.group_stock_manager'):
            return True

        warehouse = self.env['stock.warehouse'].browse(warehouse_id)
        return warehouse.company_id == user.company_id or not warehouse.company_id

    def _format_notification_message(self, data):
        """Format notification message for Discuss"""
        notification_icon = '🔴' if data['notification_type'] == 'below_min' else '🟡'

        message = f"""
        <div style="padding: 10px; border-left: 4px solid {'#dc3545' if data['notification_type'] == 'below_min' else '#ffc107'};">
            <h4 style="margin: 0 0 10px 0;">{notification_icon} Reorder Alert</h4>
            <p style="margin: 5px 0;"><strong>Product:</strong> {data['product_code'] and '[' + data['product_code'] + '] ' or ''}{data['product_name']}</p>
            <p style="margin: 5px 0;"><strong>Warehouse:</strong> {data['warehouse_name']}</p>
            <p style="margin: 5px 0;"><strong>Location:</strong> {data['location_name']}</p>
            <p style="margin: 5px 0;"><strong>Current Quantity:</strong> {data['qty_available']:.2f} {data['product_uom']}</p>
            <p style="margin: 5px 0;"><strong>Min Quantity:</strong> {data['product_min_qty']:.2f} {data['product_uom']}</p>
            <p style="margin: 5px 0;"><strong>Max Quantity:</strong> {data['product_max_qty']:.2f} {data['product_uom']}</p>
            <p style="margin: 10px 0 5px 0; color: {'#dc3545' if data['notification_type'] == 'below_min' else '#ffc107'};">
                <strong>{data['message']}</strong>
            </p>
            <p style="margin: 10px 0 0 0; font-size: 12px; color: #6c757d;">
                Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </p>
        </div>
        """
        return message

    @api.model
    def check_and_send_reorder_notifications(self):
        """Check all reordering rules and send notifications (Called by cron)"""
        # Skip if discuss.channel not available
        if 'discuss.channel' not in self.env:
            return

        orderpoints = self.search([])

        for orderpoint in orderpoints:
            try:
                # Skip if notification was sent in last 4 hours
                if orderpoint.last_notification_date:
                    time_diff = datetime.now() - orderpoint.last_notification_date
                    if time_diff < timedelta(hours=4):
                        continue

                product = orderpoint.product_id
                location = orderpoint.location_id

                # Get on-hand quantity
                qty_available = product.with_context(location=location.id).qty_available

                notification_type = False
                message = ""

                # Check if below minimum
                if qty_available < orderpoint.product_min_qty:
                    notification_type = 'below_min'
                    shortage = orderpoint.product_min_qty - qty_available
                    message = f"⚠️ Below minimum! Shortage: {shortage:.2f} {product.uom_id.name}"

                # Check if above maximum
                elif qty_available > orderpoint.product_max_qty:
                    notification_type = 'above_max'
                    excess = qty_available - orderpoint.product_max_qty
                    message = f"⚠️ Above maximum! Excess: {excess:.2f} {product.uom_id.name}"

                # Send notification if needed
                if notification_type:
                    notification_data = {
                        'product_id': product.id,
                        'product_name': product.name,
                        'product_code': product.default_code or '',
                        'warehouse_id': orderpoint.warehouse_id.id,
                        'warehouse_name': orderpoint.warehouse_id.name,
                        'location_name': location.complete_name,
                        'qty_available': qty_available,
                        'product_min_qty': orderpoint.product_min_qty,
                        'product_max_qty': orderpoint.product_max_qty,
                        'product_uom': product.uom_id.name,
                        'notification_type': notification_type,
                        'message': message,
                    }

                    orderpoint._send_notification_to_discuss(notification_data)
                    orderpoint.last_notification_date = fields.Datetime.now()
            except Exception as e:
                # Log error but continue processing other orderpoints
                continue

    def action_send_notification_now(self):
        """Manual button to send notification immediately"""
        for orderpoint in self:
            try:
                product = orderpoint.product_id
                location = orderpoint.location_id
                qty_available = product.with_context(location=location.id).qty_available

                notification_type = False
                message = ""

                if qty_available < orderpoint.product_min_qty:
                    notification_type = 'below_min'
                    shortage = orderpoint.product_min_qty - qty_available
                    message = f"⚠️ Below minimum! Shortage: {shortage:.2f} {product.uom_id.name}"
                elif qty_available > orderpoint.product_max_qty:
                    notification_type = 'above_max'
                    excess = qty_available - orderpoint.product_max_qty
                    message = f"⚠️ Above maximum! Excess: {excess:.2f} {product.uom_id.name}"

                if notification_type:
                    notification_data = {
                        'product_id': product.id,
                        'product_name': product.name,
                        'product_code': product.default_code or '',
                        'warehouse_id': orderpoint.warehouse_id.id,
                        'warehouse_name': orderpoint.warehouse_id.name,
                        'location_name': location.complete_name,
                        'qty_available': qty_available,
                        'product_min_qty': orderpoint.product_min_qty,
                        'product_max_qty': orderpoint.product_max_qty,
                        'product_uom': product.uom_id.name,
                        'notification_type': notification_type,
                        'message': message,
                    }
                    orderpoint._send_notification_to_discuss(notification_data)
                    orderpoint.last_notification_date = fields.Datetime.now()

                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': 'Notification Sent',
                            'message': 'Reorder notification has been sent to warehouse users in Discuss.',
                            'type': 'success',
                            'sticky': False,
                        }
                    }
                else:
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': 'No Alert',
                            'message': 'Current quantity is within min/max range. No notification needed.',
                            'type': 'info',
                            'sticky': False,
                        }
                    }
            except Exception as e:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Error',
                        'message': f'Error sending notification: {str(e)}',
                        'type': 'danger',
                        'sticky': False,
                    }
                }

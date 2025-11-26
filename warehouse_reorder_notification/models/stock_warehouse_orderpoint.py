from odoo import models, fields, api
from datetime import datetime, timedelta


class StockWarehouseOrderpoint(models.Model):
    _inherit = 'stock.warehouse.orderpoint'

    last_notification_date = fields.Datetime(
        string='Last Notification Date',
        help='Last time a notification was sent for this reordering rule'
    )

    def _send_notification_to_warehouse_channel(self, notification_data):
        """Send notification to warehouse-specific channel"""
        self.ensure_one()

        # Check if discuss.channel exists
        if 'discuss.channel' not in self.env:
            return False

        warehouse = self.warehouse_id
        if not warehouse:
            return False

        # Get or create channel
        channel = warehouse._get_or_create_notification_channel()

        if not channel:
            return False

        # Format message
        message_body = self._format_notification_message(notification_data)

        # Post message to channel
        channel.sudo().message_post(
            body=message_body,
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
        )

        return True

    def _format_notification_message(self, data):
        """Format notification message for channel"""
        notification_icon = '🔴' if data['notification_type'] == 'below_min' else '🟡'
        notification_color = '#dc3545' if data['notification_type'] == 'below_min' else '#ffc107'

        message = f"""
        <div style="padding: 15px; border-left: 5px solid {notification_color}; background-color: #f8f9fa; margin: 10px 0; border-radius: 4px;">
            <h4 style="margin: 0 0 15px 0; color: {notification_color};">{notification_icon} REORDER ALERT</h4>

            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 5px; font-weight: bold; width: 40%;">Product:</td>
                    <td style="padding: 5px;">{data['product_code'] and '[' + data['product_code'] + '] ' or ''}{data['product_name']}</td>
                </tr>
                <tr>
                    <td style="padding: 5px; font-weight: bold;">Warehouse:</td>
                    <td style="padding: 5px;">{data['warehouse_name']}</td>
                </tr>
                <tr>
                    <td style="padding: 5px; font-weight: bold;">Location:</td>
                    <td style="padding: 5px;">{data['location_name']}</td>
                </tr>
                <tr style="background-color: #e9ecef;">
                    <td style="padding: 5px; font-weight: bold;">Current Quantity:</td>
                    <td style="padding: 5px; font-weight: bold; color: {notification_color};">{data['qty_available']:.2f} {data['product_uom']}</td>
                </tr>
                <tr>
                    <td style="padding: 5px; font-weight: bold;">Min Quantity:</td>
                    <td style="padding: 5px;">{data['product_min_qty']:.2f} {data['product_uom']}</td>
                </tr>
                <tr>
                    <td style="padding: 5px; font-weight: bold;">Max Quantity:</td>
                    <td style="padding: 5px;">{data['product_max_qty']:.2f} {data['product_uom']}</td>
                </tr>
            </table>

            <div style="margin-top: 15px; padding: 10px; background-color: {'#f8d7da' if data['notification_type'] == 'below_min' else '#fff3cd'}; border-radius: 4px;">
                <strong style="color: {notification_color};">{data['message']}</strong>
            </div>

            <div style="margin-top: 10px; font-size: 12px; color: #6c757d; text-align: right;">
                ⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </div>
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
        notifications_sent = 0

        for orderpoint in orderpoints:
            try:
                # Skip if no warehouse
                if not orderpoint.warehouse_id:
                    continue

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
                    message = f"⚠️ URGENT: Stock is below minimum! Shortage: {shortage:.2f} {product.uom_id.name}"

                # Check if above maximum
                elif qty_available > orderpoint.product_max_qty:
                    notification_type = 'above_max'
                    excess = qty_available - orderpoint.product_max_qty
                    message = f"⚠️ WARNING: Stock is above maximum! Excess: {excess:.2f} {product.uom_id.name}"

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

                    if orderpoint._send_notification_to_warehouse_channel(notification_data):
                        orderpoint.last_notification_date = fields.Datetime.now()
                        notifications_sent += 1

            except Exception as e:
                # Log error but continue processing
                continue

        return notifications_sent

    def action_send_notification_now(self):
        """Manual button to send notification immediately"""
        self.ensure_one()

        try:
            if not self.warehouse_id:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Error',
                        'message': 'No warehouse defined for this reordering rule.',
                        'type': 'warning',
                        'sticky': False,
                    }
                }

            product = self.product_id
            location = self.location_id
            qty_available = product.with_context(location=location.id).qty_available

            notification_type = False
            message = ""

            if qty_available < self.product_min_qty:
                notification_type = 'below_min'
                shortage = self.product_min_qty - qty_available
                message = f"⚠️ URGENT: Stock is below minimum! Shortage: {shortage:.2f} {product.uom_id.name}"
            elif qty_available > self.product_max_qty:
                notification_type = 'above_max'
                excess = qty_available - self.product_max_qty
                message = f"⚠️ WARNING: Stock is above maximum! Excess: {excess:.2f} {product.uom_id.name}"

            if notification_type:
                notification_data = {
                    'product_id': product.id,
                    'product_name': product.name,
                    'product_code': product.default_code or '',
                    'warehouse_id': self.warehouse_id.id,
                    'warehouse_name': self.warehouse_id.name,
                    'location_name': location.complete_name,
                    'qty_available': qty_available,
                    'product_min_qty': self.product_min_qty,
                    'product_max_qty': self.product_max_qty,
                    'product_uom': product.uom_id.name,
                    'notification_type': notification_type,
                    'message': message,
                }

                if self._send_notification_to_warehouse_channel(notification_data):
                    self.last_notification_date = fields.Datetime.now()

                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': '✅ Notification Sent',
                            'message': f'Reorder notification sent to {self.warehouse_id.name} channel.',
                            'type': 'success',
                            'sticky': False,
                        }
                    }
                else:
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': 'Error',
                            'message': 'Could not send notification. Channel may not exist.',
                            'type': 'danger',
                            'sticky': False,
                        }
                    }
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'No Alert Needed',
                        'message': 'Current quantity is within min/max range.',
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
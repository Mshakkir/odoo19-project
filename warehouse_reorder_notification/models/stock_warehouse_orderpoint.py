from odoo import models, fields, api, _
from datetime import datetime, timedelta


class StockWarehouseOrderpoint(models.Model):
    _inherit = 'stock.warehouse.orderpoint'

    last_notification_date = fields.Datetime(
        string='Last Notification Date',
        help='Last time a notification was sent for this reordering rule'
    )

    notification_count = fields.Integer(
        string='Notifications Sent',
        default=0,
        help='Number of notifications sent for this rule'
    )

    def _send_system_notification(self, notification_data):
        """Send notification to Odoo notification center (bell icon)"""
        self.ensure_one()
        warehouse = self.warehouse_id

        if not warehouse or not warehouse.enable_reorder_notifications:
            return False

        # Get users to notify - ONLY for THIS warehouse
        users_to_notify = warehouse.sudo()._get_notification_users()

        if not users_to_notify:
            return False

        # Create notification title
        notification_icon = '🔴' if notification_data['notification_type'] == 'below_min' else '🟡'
        title = f"{notification_icon} [{notification_data['warehouse_name']}] {notification_data['product_name']}"

        # Create notification message
        message_body = self._format_notification_message_simple(notification_data)

        # Send notification ONLY to users assigned to THIS warehouse
        notifications = []
        for user in users_to_notify:
            try:
                # Create activity for tracking - specific to this warehouse
                self.env['mail.activity'].sudo().create({
                    'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                    'summary': title,
                    'note': message_body,
                    'res_id': self.id,
                    'res_model_id': self.env['ir.model']._get_id('stock.warehouse.orderpoint'),
                    'user_id': user.id,
                    'date_deadline': fields.Date.today(),
                })

                # Send browser notification
                notifications.append([
                    user.partner_id,
                    'mail.activity/updated',
                    {
                        'type': 'activity_updated',
                        'activity_created': True,
                    }
                ])
            except Exception as e:
                continue

        # Send all notifications via bus
        if notifications:
            self.env['bus.bus'].sudo()._sendmany(notifications)

        return True

    def _format_notification_message_simple(self, data):
        """Format simple notification message"""
        notification_color = '#dc3545' if data['notification_type'] == 'below_min' else '#ffc107'

        message = f"""
        <div style="padding: 10px; border-left: 4px solid {notification_color}; background-color: #f8f9fa;">
            <h4 style="margin: 0 0 10px 0; color: {notification_color};">
                {'🔴 URGENT REORDER ALERT' if data['notification_type'] == 'below_min' else '🟡 REORDER WARNING'}
            </h4>
            <table style="width: 100%; font-size: 13px;">
                <tr>
                    <td style="padding: 3px; font-weight: bold;">Product:</td>
                    <td style="padding: 3px;">{data['product_code'] and '[' + data['product_code'] + '] ' or ''}{data['product_name']}</td>
                </tr>
                <tr style="background-color: #fff3cd;">
                    <td style="padding: 3px; font-weight: bold;">Warehouse:</td>
                    <td style="padding: 3px; font-weight: bold;">{data['warehouse_name']}</td>
                </tr>
                <tr>
                    <td style="padding: 3px; font-weight: bold;">Location:</td>
                    <td style="padding: 3px;">{data['location_name']}</td>
                </tr>
                <tr style="background-color: #fff;">
                    <td style="padding: 3px; font-weight: bold;">Current Qty:</td>
                    <td style="padding: 3px; font-weight: bold; color: {notification_color};">{data['qty_available']:.2f} {data['product_uom']}</td>
                </tr>
                <tr>
                    <td style="padding: 3px; font-weight: bold;">Min Qty:</td>
                    <td style="padding: 3px;">{data['product_min_qty']:.2f} {data['product_uom']}</td>
                </tr>
                <tr>
                    <td style="padding: 3px; font-weight: bold;">Max Qty:</td>
                    <td style="padding: 3px;">{data['product_max_qty']:.2f} {data['product_uom']}</td>
                </tr>
            </table>
            <div style="margin-top: 10px; padding: 8px; background-color: {'#f8d7da' if data['notification_type'] == 'below_min' else '#fff3cd'}; border-radius: 3px;">
                <strong>{data['message']}</strong>
            </div>
            <div style="margin-top: 8px; font-size: 11px; color: #6c757d;">
                {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </div>
        </div>
        """
        return message

    @api.model
    def check_and_send_reorder_notifications(self):
        """Check all reordering rules and send notifications (Called by cron)"""
        # Get all warehouses with notifications enabled
        warehouses = self.env['stock.warehouse'].sudo().search([
            ('enable_reorder_notifications', '=', True)
        ])

        notifications_sent = 0

        # Process each warehouse separately
        for warehouse in warehouses:
            # Get users for THIS specific warehouse
            warehouse_users = warehouse.sudo()._get_notification_users()

            if not warehouse_users:
                continue

            # Get orderpoints ONLY for this warehouse
            orderpoints = self.sudo().search([
                ('warehouse_id', '=', warehouse.id),
                ('warehouse_id.enable_reorder_notifications', '=', True)
            ])

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
                        message = f"⚠️ URGENT: Stock below minimum! Shortage: {shortage:.2f} {product.uom_id.name}"
                    # Check if above maximum
                    elif qty_available > orderpoint.product_max_qty:
                        notification_type = 'above_max'
                        excess = qty_available - orderpoint.product_max_qty
                        message = f"⚠️ WARNING: Stock above maximum! Excess: {excess:.2f} {product.uom_id.name}"

                    # Send notification if needed
                    if notification_type:
                        notification_data = {
                            'product_id': product.id,
                            'product_name': product.name,
                            'product_code': product.default_code or '',
                            'warehouse_id': warehouse.id,
                            'warehouse_name': warehouse.name,
                            'location_name': location.complete_name,
                            'qty_available': qty_available,
                            'product_min_qty': orderpoint.product_min_qty,
                            'product_max_qty': orderpoint.product_max_qty,
                            'product_uom': product.uom_id.name,
                            'notification_type': notification_type,
                            'message': message,
                        }

                        if orderpoint._send_system_notification(notification_data):
                            orderpoint.write({
                                'last_notification_date': fields.Datetime.now(),
                                'notification_count': orderpoint.notification_count + 1,
                            })
                            notifications_sent += 1

                except Exception as e:
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
                        'title': _('Error'),
                        'message': _('No warehouse defined for this reordering rule.'),
                        'type': 'warning',
                        'sticky': False,
                    }
                }

            if not self.warehouse_id.enable_reorder_notifications:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Disabled'),
                        'message': _('Notifications are disabled for this warehouse.'),
                        'type': 'info',
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
                message = f"⚠️ URGENT: Stock below minimum! Shortage: {shortage:.2f} {product.uom_id.name}"
            elif qty_available > self.product_max_qty:
                notification_type = 'above_max'
                excess = qty_available - self.product_max_qty
                message = f"⚠️ WARNING: Stock above maximum! Excess: {excess:.2f} {product.uom_id.name}"

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

                if self._send_system_notification(notification_data):
                    self.write({
                        'last_notification_date': fields.Datetime.now(),
                        'notification_count': self.notification_count + 1,
                    })

                    users_count = len(self.warehouse_id._get_notification_users())
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': _('✅ Notification Sent'),
                            'message': _('Reorder notification sent to %s user(s) for %s warehouse ONLY.') % (
                                users_count, self.warehouse_id.name),
                            'type': 'success',
                            'sticky': False,
                        }
                    }
                else:
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': _('Error'),
                            'message': _('Could not send notification. Check configuration.'),
                            'type': 'danger',
                            'sticky': False,
                        }
                    }
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('No Alert Needed'),
                        'message': _('Current quantity (%.2f %s) is within min/max range.') % (qty_available,
                                                                                               product.uom_id.name),
                        'type': 'info',
                        'sticky': False,
                    }
                }

        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _('Error sending notification: %s') % str(e),
                    'type': 'danger',
                    'sticky': False,
                }
            }

    def action_view_notifications(self):
        """View all notifications/activities for this orderpoint"""
        self.ensure_one()
        return {
            'name': _('Reorder Notifications'),
            'type': 'ir.actions.act_window',
            'res_model': 'mail.activity',
            'view_mode': 'tree,form',
            'domain': [
                ('res_id', '=', self.id),
                ('res_model', '=', 'stock.warehouse.orderpoint')
            ],
            'context': {'default_res_id': self.id, 'default_res_model': 'stock.warehouse.orderpoint'},
        }

    # ============================================
    # NEW METHOD: Combined Purchase Order
    # ============================================
    def action_create_combined_purchase_order(self):
        """Create ONE combined purchase order for ALL selected products
        NO vendor restriction - user can change vendor in PO form
        """
        if not self:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Records Selected'),
                    'message': _('Please select at least one reordering rule.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }

        # Collect all orderpoints data
        orderpoints_data = []
        default_vendor = False

        for orderpoint in self:
            product = orderpoint.product_id
            location = orderpoint.location_id

            # Get quantity to order
            qty_available = product.with_context(location=location.id).qty_available

            # Calculate qty to order - only if below minimum
            if qty_available < orderpoint.product_min_qty:
                qty_to_order = orderpoint.product_max_qty - qty_available

                if qty_to_order > 0:
                    # Get vendor from product (if available)
                    vendor = False
                    price = 0.0

                    if product.seller_ids:
                        vendor = product.seller_ids[0].partner_id
                        price = product.seller_ids[0].price

                        # Use first vendor found as default
                        if not default_vendor:
                            default_vendor = vendor

                    orderpoints_data.append({
                        'orderpoint': orderpoint,
                        'product': product,
                        'qty_to_order': qty_to_order,
                        'vendor': vendor,
                        'price': price,
                    })

        if not orderpoints_data:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Orders Needed'),
                    'message': _('All selected products have sufficient stock or are above minimum quantity.'),
                    'type': 'info',
                    'sticky': False,
                }
            }

        # Get warehouse from first orderpoint
        warehouse = self[0].warehouse_id

        # Create purchase order with default vendor (or empty if none found)
        po_vals = {
            'date_order': fields.Datetime.now(),
            'origin': f'Combined Reorder - {warehouse.name}',
            'picking_type_id': warehouse.in_type_id.id,
        }

        # Add vendor if we found one
        if default_vendor:
            po_vals['partner_id'] = default_vendor.id

        # Create purchase order
        purchase_order = self.env['purchase.order'].sudo().create(po_vals)

        # Create order lines for all products
        lines_created = 0
        products_list = []

        for op_data in orderpoints_data:
            product = op_data['product']
            qty = op_data['qty_to_order']
            price = op_data['price']
            orderpoint = op_data['orderpoint']

            line_vals = {
                'order_id': purchase_order.id,
                'product_id': product.id,
                'product_qty': qty,
                'product_uom': product.uom_po_id.id,
                'price_unit': price,
                'date_planned': fields.Datetime.now(),
                'name': product.display_name,
            }

            self.env['purchase.order.line'].sudo().create(line_vals)
            lines_created += 1
            products_list.append(product.display_name)

            # Update orderpoint tracking
            orderpoint.sudo().write({
                'last_notification_date': fields.Datetime.now(),
            })

        # Return action to open the created purchase order
        return {
            'type': 'ir.actions.act_window',
            'name': _('Combined Purchase Order Created'),
            'res_model': 'purchase.order',
            'res_id': purchase_order.id,
            'view_mode': 'form',
            'target': 'current',
        }






# from odoo import models, fields, api, _
# from datetime import datetime, timedelta
#
#
# class StockWarehouseOrderpoint(models.Model):
#     _inherit = 'stock.warehouse.orderpoint'
#
#     last_notification_date = fields.Datetime(
#         string='Last Notification Date',
#         help='Last time a notification was sent for this reordering rule'
#     )
#
#     notification_count = fields.Integer(
#         string='Notifications Sent',
#         default=0,
#         help='Number of notifications sent for this rule'
#     )
#
#     def _send_system_notification(self, notification_data):
#         """Send notification to Odoo notification center (bell icon)"""
#         self.ensure_one()
#         warehouse = self.warehouse_id
#
#         if not warehouse or not warehouse.enable_reorder_notifications:
#             return False
#
#         # Get users to notify - ONLY for THIS warehouse
#         users_to_notify = warehouse.sudo()._get_notification_users()
#
#         if not users_to_notify:
#             return False
#
#         # Create notification title
#         notification_icon = '🔴' if notification_data['notification_type'] == 'below_min' else '🟡'
#         title = f"{notification_icon} [{notification_data['warehouse_name']}] {notification_data['product_name']}"
#
#         # Create notification message
#         message_body = self._format_notification_message_simple(notification_data)
#
#         # Send notification ONLY to users assigned to THIS warehouse
#         notifications = []
#         for user in users_to_notify:
#             try:
#                 # Create activity for tracking - specific to this warehouse
#                 self.env['mail.activity'].sudo().create({
#                     'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
#                     'summary': title,
#                     'note': message_body,
#                     'res_id': self.id,
#                     'res_model_id': self.env['ir.model']._get_id('stock.warehouse.orderpoint'),
#                     'user_id': user.id,
#                     'date_deadline': fields.Date.today(),
#                 })
#
#                 # Send browser notification
#                 notifications.append([
#                     user.partner_id,
#                     'mail.activity/updated',
#                     {
#                         'type': 'activity_updated',
#                         'activity_created': True,
#                     }
#                 ])
#             except Exception as e:
#                 continue
#
#         # Send all notifications via bus
#         if notifications:
#             self.env['bus.bus'].sudo()._sendmany(notifications)
#
#         return True
#
#     def _format_notification_message_simple(self, data):
#         """Format simple notification message"""
#         notification_color = '#dc3545' if data['notification_type'] == 'below_min' else '#ffc107'
#
#         message = f"""
#         <div style="padding: 10px; border-left: 4px solid {notification_color}; background-color: #f8f9fa;">
#             <h4 style="margin: 0 0 10px 0; color: {notification_color};">
#                 {'🔴 URGENT REORDER ALERT' if data['notification_type'] == 'below_min' else '🟡 REORDER WARNING'}
#             </h4>
#             <table style="width: 100%; font-size: 13px;">
#                 <tr>
#                     <td style="padding: 3px; font-weight: bold;">Product:</td>
#                     <td style="padding: 3px;">{data['product_code'] and '[' + data['product_code'] + '] ' or ''}{data['product_name']}</td>
#                 </tr>
#                 <tr style="background-color: #fff3cd;">
#                     <td style="padding: 3px; font-weight: bold;">Warehouse:</td>
#                     <td style="padding: 3px; font-weight: bold;">{data['warehouse_name']}</td>
#                 </tr>
#                 <tr>
#                     <td style="padding: 3px; font-weight: bold;">Location:</td>
#                     <td style="padding: 3px;">{data['location_name']}</td>
#                 </tr>
#                 <tr style="background-color: #fff;">
#                     <td style="padding: 3px; font-weight: bold;">Current Qty:</td>
#                     <td style="padding: 3px; font-weight: bold; color: {notification_color};">{data['qty_available']:.2f} {data['product_uom']}</td>
#                 </tr>
#                 <tr>
#                     <td style="padding: 3px; font-weight: bold;">Min Qty:</td>
#                     <td style="padding: 3px;">{data['product_min_qty']:.2f} {data['product_uom']}</td>
#                 </tr>
#                 <tr>
#                     <td style="padding: 3px; font-weight: bold;">Max Qty:</td>
#                     <td style="padding: 3px;">{data['product_max_qty']:.2f} {data['product_uom']}</td>
#                 </tr>
#             </table>
#             <div style="margin-top: 10px; padding: 8px; background-color: {'#f8d7da' if data['notification_type'] == 'below_min' else '#fff3cd'}; border-radius: 3px;">
#                 <strong>{data['message']}</strong>
#             </div>
#             <div style="margin-top: 8px; font-size: 11px; color: #6c757d;">
#                 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
#             </div>
#         </div>
#         """
#         return message
#
#     @api.model
#     def check_and_send_reorder_notifications(self):
#         """Check all reordering rules and send notifications (Called by cron)
#         FIXED: Now processes warehouse by warehouse to ensure proper user targeting
#         """
#         # Get all warehouses with notifications enabled
#         warehouses = self.env['stock.warehouse'].sudo().search([
#             ('enable_reorder_notifications', '=', True)
#         ])
#
#         notifications_sent = 0
#
#         # Process each warehouse separately
#         for warehouse in warehouses:
#             # Get users for THIS specific warehouse
#             warehouse_users = warehouse.sudo()._get_notification_users()
#
#             if not warehouse_users:
#                 continue
#
#             # Get orderpoints ONLY for this warehouse - use sudo to bypass access rules
#             orderpoints = self.sudo().search([
#                 ('warehouse_id', '=', warehouse.id),
#                 ('warehouse_id.enable_reorder_notifications', '=', True)
#             ])
#
#             for orderpoint in orderpoints:
#                 try:
#                     # Skip if notification was sent in last 4 hours
#                     if orderpoint.last_notification_date:
#                         time_diff = datetime.now() - orderpoint.last_notification_date
#                         if time_diff < timedelta(hours=4):
#                             continue
#
#                     product = orderpoint.product_id
#                     location = orderpoint.location_id
#
#                     # Get on-hand quantity
#                     qty_available = product.with_context(location=location.id).qty_available
#
#                     notification_type = False
#                     message = ""
#
#                     # Check if below minimum
#                     if qty_available < orderpoint.product_min_qty:
#                         notification_type = 'below_min'
#                         shortage = orderpoint.product_min_qty - qty_available
#                         message = f"⚠️ URGENT: Stock below minimum! Shortage: {shortage:.2f} {product.uom_id.name}"
#                     # Check if above maximum
#                     elif qty_available > orderpoint.product_max_qty:
#                         notification_type = 'above_max'
#                         excess = qty_available - orderpoint.product_max_qty
#                         message = f"⚠️ WARNING: Stock above maximum! Excess: {excess:.2f} {product.uom_id.name}"
#
#                     # Send notification if needed - will only go to THIS warehouse's users
#                     if notification_type:
#                         notification_data = {
#                             'product_id': product.id,
#                             'product_name': product.name,
#                             'product_code': product.default_code or '',
#                             'warehouse_id': warehouse.id,
#                             'warehouse_name': warehouse.name,
#                             'location_name': location.complete_name,
#                             'qty_available': qty_available,
#                             'product_min_qty': orderpoint.product_min_qty,
#                             'product_max_qty': orderpoint.product_max_qty,
#                             'product_uom': product.uom_id.name,
#                             'notification_type': notification_type,
#                             'message': message,
#                         }
#
#                         if orderpoint._send_system_notification(notification_data):
#                             orderpoint.write({
#                                 'last_notification_date': fields.Datetime.now(),
#                                 'notification_count': orderpoint.notification_count + 1,
#                             })
#                             notifications_sent += 1
#
#                 except Exception as e:
#                     # Log error but continue processing
#                     continue
#
#         return notifications_sent
#
#     def action_send_notification_now(self):
#         """Manual button to send notification immediately"""
#         self.ensure_one()
#
#         try:
#             if not self.warehouse_id:
#                 return {
#                     'type': 'ir.actions.client',
#                     'tag': 'display_notification',
#                     'params': {
#                         'title': _('Error'),
#                         'message': _('No warehouse defined for this reordering rule.'),
#                         'type': 'warning',
#                         'sticky': False,
#                     }
#                 }
#
#             if not self.warehouse_id.enable_reorder_notifications:
#                 return {
#                     'type': 'ir.actions.client',
#                     'tag': 'display_notification',
#                     'params': {
#                         'title': _('Disabled'),
#                         'message': _('Notifications are disabled for this warehouse.'),
#                         'type': 'info',
#                         'sticky': False,
#                     }
#                 }
#
#             product = self.product_id
#             location = self.location_id
#             qty_available = product.with_context(location=location.id).qty_available
#
#             notification_type = False
#             message = ""
#
#             if qty_available < self.product_min_qty:
#                 notification_type = 'below_min'
#                 shortage = self.product_min_qty - qty_available
#                 message = f"⚠️ URGENT: Stock below minimum! Shortage: {shortage:.2f} {product.uom_id.name}"
#             elif qty_available > self.product_max_qty:
#                 notification_type = 'above_max'
#                 excess = qty_available - self.product_max_qty
#                 message = f"⚠️ WARNING: Stock above maximum! Excess: {excess:.2f} {product.uom_id.name}"
#
#             if notification_type:
#                 notification_data = {
#                     'product_id': product.id,
#                     'product_name': product.name,
#                     'product_code': product.default_code or '',
#                     'warehouse_id': self.warehouse_id.id,
#                     'warehouse_name': self.warehouse_id.name,
#                     'location_name': location.complete_name,
#                     'qty_available': qty_available,
#                     'product_min_qty': self.product_min_qty,
#                     'product_max_qty': self.product_max_qty,
#                     'product_uom': product.uom_id.name,
#                     'notification_type': notification_type,
#                     'message': message,
#                 }
#
#                 if self._send_system_notification(notification_data):
#                     self.write({
#                         'last_notification_date': fields.Datetime.now(),
#                         'notification_count': self.notification_count + 1,
#                     })
#
#                     users_count = len(self.warehouse_id._get_notification_users())
#                     return {
#                         'type': 'ir.actions.client',
#                         'tag': 'display_notification',
#                         'params': {
#                             'title': _('✅ Notification Sent'),
#                             'message': _('Reorder notification sent to %s user(s) for %s warehouse ONLY.') % (
#                                 users_count, self.warehouse_id.name),
#                             'type': 'success',
#                             'sticky': False,
#                         }
#                     }
#                 else:
#                     return {
#                         'type': 'ir.actions.client',
#                         'tag': 'display_notification',
#                         'params': {
#                             'title': _('Error'),
#                             'message': _('Could not send notification. Check configuration.'),
#                             'type': 'danger',
#                             'sticky': False,
#                         }
#                     }
#             else:
#                 return {
#                     'type': 'ir.actions.client',
#                     'tag': 'display_notification',
#                     'params': {
#                         'title': _('No Alert Needed'),
#                         'message': _('Current quantity (%.2f %s) is within min/max range.') % (qty_available,
#                                                                                                product.uom_id.name),
#                         'type': 'info',
#                         'sticky': False,
#                     }
#                 }
#
#         except Exception as e:
#             return {
#                 'type': 'ir.actions.client',
#                 'tag': 'display_notification',
#                 'params': {
#                     'title': _('Error'),
#                     'message': _('Error sending notification: %s') % str(e),
#                     'type': 'danger',
#                     'sticky': False,
#                 }
#             }
#
#     def action_view_notifications(self):
#         """View all notifications/activities for this orderpoint"""
#         self.ensure_one()
#         return {
#             'name': _('Reorder Notifications'),
#             'type': 'ir.actions.act_window',
#             'res_model': 'mail.activity',
#             'view_mode': 'tree,form',
#             'domain': [
#                 ('res_id', '=', self.id),
#                 ('res_model', '=', 'stock.warehouse.orderpoint')
#             ],
#             'context': {'default_res_id': self.id, 'default_res_model': 'stock.warehouse.orderpoint'},
#         }

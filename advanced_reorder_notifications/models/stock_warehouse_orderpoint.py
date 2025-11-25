from odoo import models, fields, api, _
from odoo.tools import format_datetime
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class StockWarehouseOrderpoint(models.Model):
    _inherit = 'stock.warehouse.orderpoint'

    notification_sent = fields.Boolean(string='Notification Sent', default=False)
    last_notification_date = fields.Datetime(string='Last Notification Date')
    notify_on_reorder = fields.Boolean(string='Send Notifications Only', default=True,
                                       help="Enable notifications without creating automatic purchase orders")
    disable_auto_purchase = fields.Boolean(string='Disable Auto Purchase Orders', default=True,
                                           help="Prevent automatic purchase order creation. Only send notifications.")

    def _get_qty_on_hand(self):
        """Get current quantity on hand (actual stock, not forecast)"""
        self.ensure_one()

        # Using stock quants for actual on-hand quantity
        quants = self.env['stock.quant'].search([
            ('product_id', '=', self.product_id.id),
            ('location_id', '=', self.location_id.id)
        ])
        actual_qty = sum(quants.mapped('quantity'))

        _logger.info(f"Product {self.product_id.name}: Qty on hand = {actual_qty}, Min = {self.product_min_qty}")

        return actual_qty

    def _should_send_notification(self):
        """Check if notification should be sent"""
        self.ensure_one()

        # Only check if notifications are enabled
        if not self.notify_on_reorder:
            return False

        qty_on_hand = self._get_qty_on_hand()

        # Check if below minimum
        if qty_on_hand <= self.product_min_qty:
            # Allow re-notification after 24 hours
            if self.notification_sent and self.last_notification_date:
                time_since_last = fields.Datetime.now() - self.last_notification_date
                if time_since_last < timedelta(hours=24):
                    _logger.info(f"Skipping notification for {self.product_id.name} - sent recently")
                    return False  # Too soon, don't resend
            _logger.info(f"Should send notification for {self.product_id.name}")
            return True

        # Reset notification flag if stock is back above minimum
        if qty_on_hand > self.product_min_qty and self.notification_sent:
            self.write({
                'notification_sent': False,
                'last_notification_date': False
            })

        return False

    def _get_reorder_details(self):
        """Prepare detailed reorder information"""
        self.ensure_one()

        qty_on_hand = self._get_qty_on_hand()
        qty_to_order = max(0, self.product_max_qty - qty_on_hand)

        # Get vendor information
        vendor = self.product_id.seller_ids[0] if self.product_id.seller_ids else False
        vendor_name = vendor.partner_id.name if vendor else 'No Vendor Set'
        vendor_price = vendor.price if vendor else 0.0
        lead_time = vendor.delay if vendor else 0

        # Calculate estimated cost
        estimated_cost = qty_to_order * vendor_price

        # Get warehouse info
        warehouse = self.warehouse_id or self.location_id.warehouse_id

        return {
            'product_name': self.product_id.display_name,
            'product_code': self.product_id.default_code or 'N/A',
            'current_qty': qty_on_hand,
            'min_qty': self.product_min_qty,
            'max_qty': self.product_max_qty,
            'qty_to_order': qty_to_order,
            'uom': self.product_uom.name,
            'vendor_name': vendor_name,
            'vendor_price': vendor_price,
            'estimated_cost': estimated_cost,
            'lead_time': lead_time,
            'warehouse': warehouse.name if warehouse else 'Unknown',
            'location': self.location_id.complete_name,
            'currency': self.env.company.currency_id.symbol,
        }

    def _get_notification_recipients(self):
        """Get list of users to notify"""
        self.ensure_one()

        recipients = self.env['res.users']

        # Get purchase users
        purchase_group = self.env.ref('purchase.group_purchase_user', raise_if_not_found=False)
        if purchase_group:
            recipients |= purchase_group.users

        # Get inventory managers
        stock_manager_group = self.env.ref('stock.group_stock_manager', raise_if_not_found=False)
        if stock_manager_group:
            recipients |= stock_manager_group.users

        # Get admins if configured
        get_param = self.env['ir.config_parameter'].sudo().get_param
        if get_param('reorder_notification.notify_admins', 'True') == 'True':
            admin_group = self.env.ref('base.group_system', raise_if_not_found=False)
            if admin_group:
                recipients |= admin_group.users

        _logger.info(f"Notification recipients: {recipients.mapped('name')}")
        return recipients

    def send_reorder_notification(self):
        """Send notification for low stock - Dashboard Only (No Email, No Auto PO)"""
        for orderpoint in self:
            if not orderpoint._should_send_notification():
                continue

            # Get reorder details
            details = orderpoint._get_reorder_details()
            recipients = orderpoint._get_notification_recipients()

            if not recipients:
                _logger.warning(f"No recipients found for {orderpoint.product_id.name}")
                continue

            _logger.info(f"Sending notification for {orderpoint.product_id.name} to {len(recipients)} users")

            # Get activity type
            activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
            if not activity_type:
                _logger.error("Activity type 'mail.mail_activity_data_todo' not found")
                continue

            # Create activity/notification in Odoo Dashboard
            for user in recipients:
                # Check if activity already exists for this user
                existing_activity = self.env['mail.activity'].search([
                    ('res_id', '=', orderpoint.id),
                    ('res_model', '=', 'stock.warehouse.orderpoint'),
                    ('user_id', '=', user.id),
                    ('activity_type_id', '=', activity_type.id),
                ], limit=1)

                if not existing_activity:
                    try:
                        # Create activity properly
                        self.env['mail.activity'].create({
                            'activity_type_id': activity_type.id,
                            'summary': f'🔔 Reorder Required: {details["product_name"]}',
                            'note': f"""
                                <div style="font-family: Arial, sans-serif; padding: 15px; background-color: #fff3cd; border-left: 4px solid #ffc107; border-radius: 5px;">
                                    <h3 style="color: #856404; margin-top: 0;">⚠️ Low Stock Alert</h3>

                                    <div style="background-color: white; padding: 15px; border-radius: 5px; margin: 10px 0;">
                                        <h4 style="color: #0066cc; margin: 0 0 10px 0;">{details['product_name']}</h4>
                                        <p style="margin: 5px 0; color: #666;"><strong>Product Code:</strong> {details['product_code']}</p>
                                    </div>

                                    <table style="width: 100%; border-collapse: collapse; margin: 15px 0; background-color: white;">
                                        <tr style="background-color: #f8f9fa;">
                                            <td style="padding: 10px; border: 1px solid #dee2e6; font-weight: bold;">Current Stock:</td>
                                            <td style="padding: 10px; border: 1px solid #dee2e6; color: #dc3545; font-weight: bold; font-size: 16px;">
                                                {details['current_qty']} {details['uom']}
                                            </td>
                                        </tr>
                                        <tr>
                                            <td style="padding: 10px; border: 1px solid #dee2e6; font-weight: bold;">Minimum Required:</td>
                                            <td style="padding: 10px; border: 1px solid #dee2e6;">{details['min_qty']} {details['uom']}</td>
                                        </tr>
                                        <tr style="background-color: #f8f9fa;">
                                            <td style="padding: 10px; border: 1px solid #dee2e6; font-weight: bold;">Maximum Level:</td>
                                            <td style="padding: 10px; border: 1px solid #dee2e6;">{details['max_qty']} {details['uom']}</td>
                                        </tr>
                                        <tr style="background-color: #d4edda;">
                                            <td style="padding: 10px; border: 1px solid #dee2e6; font-weight: bold;">Suggested Order Quantity:</td>
                                            <td style="padding: 10px; border: 1px solid #dee2e6; color: #155724; font-weight: bold; font-size: 16px;">
                                                {details['qty_to_order']} {details['uom']}
                                            </td>
                                        </tr>
                                    </table>

                                    <div style="background-color: white; padding: 15px; border-radius: 5px; margin: 10px 0;">
                                        <h4 style="color: #495057; margin: 0 0 10px 0;">📍 Location & Vendor Details</h4>
                                        <p style="margin: 5px 0;"><strong>Warehouse:</strong> {details['warehouse']}</p>
                                        <p style="margin: 5px 0;"><strong>Location:</strong> {details['location']}</p>
                                        <p style="margin: 5px 0;"><strong>Vendor:</strong> {details['vendor_name']}</p>
                                        <p style="margin: 5px 0;"><strong>Unit Price:</strong> {details['currency']}{details['vendor_price']:.2f}</p>
                                        <p style="margin: 5px 0;"><strong>Estimated Cost:</strong> <span style="color: #28a745; font-weight: bold;">{details['currency']}{details['estimated_cost']:.2f}</span></p>
                                        <p style="margin: 5px 0;"><strong>Lead Time:</strong> {details['lead_time']} days</p>
                                    </div>

                                    <div style="background-color: #e7f3ff; padding: 12px; border-radius: 5px; margin: 10px 0; border-left: 4px solid #0066cc;">
                                        <p style="margin: 0; color: #004085; font-weight: bold;">📝 Action Required:</p>
                                        <p style="margin: 5px 0 0 0; color: #004085;">Please manually create a purchase order for this product. Auto-creation is disabled.</p>
                                    </div>

                                    <div style="text-align: center; margin-top: 15px;">
                                        <p style="color: #856404; font-size: 12px; margin: 0;">Click "Mark as Done" after creating the purchase order</p>
                                    </div>
                                </div>
                            """,
                            'res_id': orderpoint.id,
                            'res_model_id': self.env['ir.model']._get('stock.warehouse.orderpoint').id,
                            'user_id': user.id,
                        })
                        _logger.info(f"Activity created for user {user.name}")
                    except Exception as e:
                        _logger.error(f"Error creating activity for {user.name}: {str(e)}")

            # Send internal message/notification (appears in chatter/inbox)
            try:
                orderpoint.message_post(
                    body=f"""
                        <div style="padding: 10px; background-color: #fff3cd; border-left: 4px solid #ffc107;">
                            <strong>🔔 Reorder Notification Sent (Manual Action Required)</strong><br/>
                            Notification sent to: {', '.join(recipients.mapped('name'))}<br/>
                            Product: {details['product_name']}<br/>
                            Current Stock: {details['current_qty']} {details['uom']} (Min: {details['min_qty']} {details['uom']})<br/>
                            Suggested Order: {details['qty_to_order']} {details['uom']}<br/>
                            <br/>
                            <em style="color: #856404;">Note: Automatic PO creation is disabled. Please create purchase order manually.</em>
                        </div>
                    """,
                    subject=f"Reorder Alert: {details['product_name']}",
                    message_type='notification',
                    subtype_xmlid='mail.mt_note',
                    partner_ids=recipients.mapped('partner_id').ids,
                )
                _logger.info(f"Message posted for {orderpoint.product_id.name}")
            except Exception as e:
                _logger.error(f"Error posting message: {str(e)}")

            # Update notification status
            orderpoint.write({
                'notification_sent': True,
                'last_notification_date': fields.Datetime.now(),
            })

    @api.model
    def check_all_reorder_rules(self):
        """Scheduled action to check all reordering rules"""
        _logger.info("=== Starting reorder rules check (Notification Only Mode) ===")

        # Get all active reordering rules with notifications enabled
        orderpoints = self.search([
            ('notify_on_reorder', '=', True),
        ])

        _logger.info(f"Found {len(orderpoints)} orderpoints with notifications enabled")

        # Check each orderpoint
        notification_count = 0
        for orderpoint in orderpoints:
            try:
                orderpoint.send_reorder_notification()
                notification_count += 1
            except Exception as e:
                # Log error but continue with other products
                _logger.error(f"Error sending notification for {orderpoint.product_id.name}: {str(e)}", exc_info=True)

        _logger.info(f"=== Reorder check complete. Processed {notification_count} notifications ===")
        return True

    @api.model
    def send_daily_summary(self):
        """Send daily summary dashboard notification (No Email)"""
        _logger.info("=== Starting daily summary ===")

        # Get all orderpoints with notifications enabled
        all_orderpoints = self.search([('notify_on_reorder', '=', True)])
        low_stock_items = []

        for op in all_orderpoints:
            qty_on_hand = op._get_qty_on_hand()
            if qty_on_hand <= op.product_min_qty:
                low_stock_items.append(op._get_reorder_details())

        if not low_stock_items:
            _logger.info("No low stock items found for daily summary")
            return True

        _logger.info(f"Found {len(low_stock_items)} low stock items")

        # Get recipients
        recipients = self.env['res.users']
        purchase_group = self.env.ref('purchase.group_purchase_user', raise_if_not_found=False)
        if purchase_group:
            recipients |= purchase_group.users

        stock_manager_group = self.env.ref('stock.group_stock_manager', raise_if_not_found=False)
        if stock_manager_group:
            recipients |= stock_manager_group.users

        if not recipients:
            _logger.warning("No recipients found for daily summary")
            return True

        # Create summary message for each user
        for user in recipients:
            # Build HTML summary
            items_html = ""
            for item in low_stock_items:
                items_html += f"""
                <div style="background-color: #f8f9fa; border-left: 4px solid #0066cc; padding: 12px; margin: 10px 0; border-radius: 5px;">
                    <h4 style="color: #0066cc; margin: 0 0 8px 0;">{item['product_name']}</h4>
                    <p style="margin: 3px 0; font-size: 13px; color: #666;">
                        <strong>Code:</strong> {item['product_code']} | 
                        <strong>Warehouse:</strong> {item['warehouse']}
                    </p>
                    <div style="margin: 8px 0;">
                        <span style="display: inline-block; background-color: #dc3545; color: white; padding: 4px 10px; border-radius: 3px; font-size: 12px; margin-right: 5px;">
                            Current: {item['current_qty']} {item['uom']}
                        </span>
                        <span style="display: inline-block; background-color: #28a745; color: white; padding: 4px 10px; border-radius: 3px; font-size: 12px;">
                            Order: {item['qty_to_order']} {item['uom']}
                        </span>
                    </div>
                    <p style="margin: 3px 0; font-size: 13px; color: #495057;">
                        <strong>Vendor:</strong> {item['vendor_name']} | 
                        <strong>Est. Cost:</strong> {item['currency']}{item['estimated_cost']:.2f}
                    </p>
                </div>
                """

            summary_body = f"""
            <div style="font-family: Arial, sans-serif; padding: 20px; background-color: white; border-radius: 8px;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                    <h2 style="color: white; margin: 0; text-align: center;">📊 Daily Reorder Summary</h2>
                    <p style="color: white; text-align: center; margin: 10px 0 0 0; font-size: 14px;">
                        {fields.Date.today().strftime('%A, %B %d, %Y')}
                    </p>
                </div>

                <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 20px; border-radius: 8px; margin-bottom: 20px; text-align: center; color: white;">
                    <h1 style="margin: 0; font-size: 48px;">{len(low_stock_items)}</h1>
                    <p style="margin: 5px 0 0 0; font-size: 16px;">Products Require Attention</p>
                </div>

                <div style="background-color: #fff3cd; padding: 12px; border-radius: 5px; margin-bottom: 20px; border-left: 4px solid #ffc107;">
                    <p style="margin: 0; color: #856404; font-weight: bold;">⚠️ Manual Action Required</p>
                    <p style="margin: 5px 0 0 0; color: #856404;">Auto-purchase is disabled. Please review and create POs manually.</p>
                </div>

                <h3 style="color: #495057; border-bottom: 2px solid #667eea; padding-bottom: 10px;">
                    📦 Products Requiring Reorder
                </h3>

                {items_html}

                <div style="margin-top: 20px; padding-top: 15px; border-top: 2px solid #e9ecef; text-align: center; color: #6c757d; font-size: 12px;">
                    <p>This is your automated daily summary from Odoo Inventory System</p>
                    <p>Generated at: {fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
            </div>
            """

            # Send notification to user
            try:
                user.partner_id.message_post(
                    body=summary_body,
                    subject=f'📊 Daily Reorder Summary - {len(low_stock_items)} Items Require Attention',
                    message_type='notification',
                    subtype_xmlid='mail.mt_note',
                )
                _logger.info(f"Daily summary sent to {user.name}")
            except Exception as e:
                _logger.error(f"Error sending daily summary to {user.name}: {str(e)}")

        _logger.info("=== Daily summary complete ===")
        return True

    # CRITICAL: Override Odoo's automatic procurement to prevent auto PO creation
    def _procure_orderpoint_confirm(self, use_new_cursor=False, company_id=False, raise_user_error=True):
        """Override to prevent automatic purchase order creation when disable_auto_purchase is True"""
        # Filter out orderpoints that have auto-purchase disabled
        orderpoints_to_process = self.filtered(lambda op: not op.disable_auto_purchase)

        if orderpoints_to_process:
            # Only process orderpoints that allow auto-purchase
            return super(StockWarehouseOrderpoint, orderpoints_to_process)._procure_orderpoint_confirm(
                use_new_cursor=use_new_cursor,
                company_id=company_id,
                raise_user_error=raise_user_error
            )

        # Log that we're skipping auto-purchase
        for op in self.filtered(lambda op: op.disable_auto_purchase):
            _logger.info(f"Skipping auto-purchase for {op.product_id.name} - notifications only mode enabled")

        return True

    def _compute_qty_to_order(self):
        """Override to show 0 qty to order when auto-purchase is disabled"""
        for orderpoint in self:
            if orderpoint.disable_auto_purchase:
                # Don't trigger automatic ordering
                orderpoint.qty_to_order = 0.0
            else:
                # Use standard Odoo calculation
                super(StockWarehouseOrderpoint, orderpoint)._compute_qty_to_order()





# from odoo import models, fields, api, _
# from odoo.tools import format_datetime
# from datetime import datetime, timedelta
# import logging
#
# _logger = logging.getLogger(__name__)
#
#
# class StockWarehouseOrderpoint(models.Model):
#     _inherit = 'stock.warehouse.orderpoint'
#
#     notification_sent = fields.Boolean(string='Notification Sent', default=False)
#     last_notification_date = fields.Datetime(string='Last Notification Date')
#     notify_on_reorder = fields.Boolean(string='Send Notifications', default=True)
#
#     def _get_qty_on_hand(self):
#         """Get current quantity on hand (actual stock, not forecast)"""
#         self.ensure_one()
#
#         # Using stock quants for actual on-hand quantity
#         quants = self.env['stock.quant'].search([
#             ('product_id', '=', self.product_id.id),
#             ('location_id', '=', self.location_id.id)
#         ])
#         actual_qty = sum(quants.mapped('quantity'))
#
#         _logger.info(f"Product {self.product_id.name}: Qty on hand = {actual_qty}, Min = {self.product_min_qty}")
#
#         return actual_qty
#
#     def _should_send_notification(self):
#         """Check if notification should be sent"""
#         self.ensure_one()
#         qty_on_hand = self._get_qty_on_hand()
#
#         # Check if below minimum and notification enabled
#         if qty_on_hand <= self.product_min_qty and self.notify_on_reorder:
#             # Allow re-notification after 24 hours
#             if self.notification_sent and self.last_notification_date:
#                 time_since_last = fields.Datetime.now() - self.last_notification_date
#                 if time_since_last < timedelta(hours=24):
#                     _logger.info(f"Skipping notification for {self.product_id.name} - sent recently")
#                     return False  # Too soon, don't resend
#             _logger.info(f"Should send notification for {self.product_id.name}")
#             return True
#
#         # Reset notification flag if stock is back above minimum
#         if qty_on_hand > self.product_min_qty and self.notification_sent:
#             self.write({
#                 'notification_sent': False,
#                 'last_notification_date': False
#             })
#
#         return False
#
#     def _get_reorder_details(self):
#         """Prepare detailed reorder information"""
#         self.ensure_one()
#
#         qty_on_hand = self._get_qty_on_hand()
#         qty_to_order = max(0, self.product_max_qty - qty_on_hand)
#
#         # Get vendor information
#         vendor = self.product_id.seller_ids[0] if self.product_id.seller_ids else False
#         vendor_name = vendor.partner_id.name if vendor else 'No Vendor Set'
#         vendor_price = vendor.price if vendor else 0.0
#         lead_time = vendor.delay if vendor else 0
#
#         # Calculate estimated cost
#         estimated_cost = qty_to_order * vendor_price
#
#         # Get warehouse info
#         warehouse = self.warehouse_id or self.location_id.warehouse_id
#
#         return {
#             'product_name': self.product_id.display_name,
#             'product_code': self.product_id.default_code or 'N/A',
#             'current_qty': qty_on_hand,
#             'min_qty': self.product_min_qty,
#             'max_qty': self.product_max_qty,
#             'qty_to_order': qty_to_order,
#             'uom': self.product_uom.name,
#             'vendor_name': vendor_name,
#             'vendor_price': vendor_price,
#             'estimated_cost': estimated_cost,
#             'lead_time': lead_time,
#             'warehouse': warehouse.name if warehouse else 'Unknown',
#             'location': self.location_id.complete_name,
#             'currency': self.env.company.currency_id.symbol,
#         }
#
#     def _get_notification_recipients(self):
#         """Get list of users to notify"""
#         self.ensure_one()
#
#         recipients = self.env['res.users']
#
#         # Get purchase users
#         purchase_group = self.env.ref('purchase.group_purchase_user', raise_if_not_found=False)
#         if purchase_group:
#             recipients |= purchase_group.users
#
#         # Get inventory managers
#         stock_manager_group = self.env.ref('stock.group_stock_manager', raise_if_not_found=False)
#         if stock_manager_group:
#             recipients |= stock_manager_group.users
#
#         # Get admins if configured
#         get_param = self.env['ir.config_parameter'].sudo().get_param
#         if get_param('reorder_notification.notify_admins', 'True') == 'True':
#             admin_group = self.env.ref('base.group_system', raise_if_not_found=False)
#             if admin_group:
#                 recipients |= admin_group.users
#
#         _logger.info(f"Notification recipients: {recipients.mapped('name')}")
#         return recipients
#
#     def send_reorder_notification(self):
#         """Send notification for low stock - Dashboard Only (No Email)"""
#         for orderpoint in self:
#             if not orderpoint._should_send_notification():
#                 continue
#
#             # Get reorder details
#             details = orderpoint._get_reorder_details()
#             recipients = orderpoint._get_notification_recipients()
#
#             if not recipients:
#                 _logger.warning(f"No recipients found for {orderpoint.product_id.name}")
#                 continue
#
#             _logger.info(f"Sending notification for {orderpoint.product_id.name} to {len(recipients)} users")
#
#             # Get activity type
#             activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
#             if not activity_type:
#                 _logger.error("Activity type 'mail.mail_activity_data_todo' not found")
#                 continue
#
#             # Create activity/notification in Odoo Dashboard
#             for user in recipients:
#                 # Check if activity already exists for this user
#                 existing_activity = self.env['mail.activity'].search([
#                     ('res_id', '=', orderpoint.id),
#                     ('res_model', '=', 'stock.warehouse.orderpoint'),
#                     ('user_id', '=', user.id),
#                     ('activity_type_id', '=', activity_type.id),
#                 ], limit=1)
#
#                 if not existing_activity:
#                     try:
#                         # Create activity properly
#                         self.env['mail.activity'].create({
#                             'activity_type_id': activity_type.id,
#                             'summary': f'🔔 Reorder Required: {details["product_name"]}',
#                             'note': f"""
#                                 <div style="font-family: Arial, sans-serif; padding: 15px; background-color: #fff3cd; border-left: 4px solid #ffc107; border-radius: 5px;">
#                                     <h3 style="color: #856404; margin-top: 0;">⚠️ Low Stock Alert</h3>
#
#                                     <div style="background-color: white; padding: 15px; border-radius: 5px; margin: 10px 0;">
#                                         <h4 style="color: #0066cc; margin: 0 0 10px 0;">{details['product_name']}</h4>
#                                         <p style="margin: 5px 0; color: #666;"><strong>Product Code:</strong> {details['product_code']}</p>
#                                     </div>
#
#                                     <table style="width: 100%; border-collapse: collapse; margin: 15px 0; background-color: white;">
#                                         <tr style="background-color: #f8f9fa;">
#                                             <td style="padding: 10px; border: 1px solid #dee2e6; font-weight: bold;">Current Stock:</td>
#                                             <td style="padding: 10px; border: 1px solid #dee2e6; color: #dc3545; font-weight: bold; font-size: 16px;">
#                                                 {details['current_qty']} {details['uom']}
#                                             </td>
#                                         </tr>
#                                         <tr>
#                                             <td style="padding: 10px; border: 1px solid #dee2e6; font-weight: bold;">Minimum Required:</td>
#                                             <td style="padding: 10px; border: 1px solid #dee2e6;">{details['min_qty']} {details['uom']}</td>
#                                         </tr>
#                                         <tr style="background-color: #f8f9fa;">
#                                             <td style="padding: 10px; border: 1px solid #dee2e6; font-weight: bold;">Maximum Level:</td>
#                                             <td style="padding: 10px; border: 1px solid #dee2e6;">{details['max_qty']} {details['uom']}</td>
#                                         </tr>
#                                         <tr style="background-color: #d4edda;">
#                                             <td style="padding: 10px; border: 1px solid #dee2e6; font-weight: bold;">Quantity to Order:</td>
#                                             <td style="padding: 10px; border: 1px solid #dee2e6; color: #155724; font-weight: bold; font-size: 16px;">
#                                                 {details['qty_to_order']} {details['uom']}
#                                             </td>
#                                         </tr>
#                                     </table>
#
#                                     <div style="background-color: white; padding: 15px; border-radius: 5px; margin: 10px 0;">
#                                         <h4 style="color: #495057; margin: 0 0 10px 0;">📍 Location & Vendor Details</h4>
#                                         <p style="margin: 5px 0;"><strong>Warehouse:</strong> {details['warehouse']}</p>
#                                         <p style="margin: 5px 0;"><strong>Location:</strong> {details['location']}</p>
#                                         <p style="margin: 5px 0;"><strong>Vendor:</strong> {details['vendor_name']}</p>
#                                         <p style="margin: 5px 0;"><strong>Unit Price:</strong> {details['currency']}{details['vendor_price']:.2f}</p>
#                                         <p style="margin: 5px 0;"><strong>Estimated Cost:</strong> <span style="color: #28a745; font-weight: bold;">{details['currency']}{details['estimated_cost']:.2f}</span></p>
#                                         <p style="margin: 5px 0;"><strong>Lead Time:</strong> {details['lead_time']} days</p>
#                                     </div>
#
#                                     <div style="text-align: center; margin-top: 15px;">
#                                         <p style="color: #856404; font-size: 12px; margin: 0;">Click "Mark as Done" after creating the purchase order</p>
#                                     </div>
#                                 </div>
#                             """,
#                             'res_id': orderpoint.id,
#                             'res_model_id': self.env['ir.model']._get('stock.warehouse.orderpoint').id,
#                             'user_id': user.id,
#                         })
#                         _logger.info(f"Activity created for user {user.name}")
#                     except Exception as e:
#                         _logger.error(f"Error creating activity for {user.name}: {str(e)}")
#
#             # Send internal message/notification (appears in chatter/inbox)
#             try:
#                 orderpoint.message_post(
#                     body=f"""
#                         <div style="padding: 10px; background-color: #fff3cd; border-left: 4px solid #ffc107;">
#                             <strong>🔔 Reorder Notification Sent</strong><br/>
#                             Notification sent to: {', '.join(recipients.mapped('name'))}<br/>
#                             Product: {details['product_name']}<br/>
#                             Current Stock: {details['current_qty']} {details['uom']} (Min: {details['min_qty']} {details['uom']})<br/>
#                             Action Required: Order {details['qty_to_order']} {details['uom']}
#                         </div>
#                     """,
#                     subject=f"Reorder Alert: {details['product_name']}",
#                     message_type='notification',
#                     subtype_xmlid='mail.mt_note',
#                     partner_ids=recipients.mapped('partner_id').ids,
#                 )
#                 _logger.info(f"Message posted for {orderpoint.product_id.name}")
#             except Exception as e:
#                 _logger.error(f"Error posting message: {str(e)}")
#
#             # Update notification status
#             orderpoint.write({
#                 'notification_sent': True,
#                 'last_notification_date': fields.Datetime.now(),
#             })
#
#     @api.model
#     def check_all_reorder_rules(self):
#         """Scheduled action to check all reordering rules"""
#         _logger.info("=== Starting reorder rules check ===")
#
#         # Get all active reordering rules
#         orderpoints = self.search([
#             ('notify_on_reorder', '=', True),
#         ])
#
#         _logger.info(f"Found {len(orderpoints)} orderpoints with notifications enabled")
#
#         # Check each orderpoint
#         notification_count = 0
#         for orderpoint in orderpoints:
#             try:
#                 orderpoint.send_reorder_notification()
#                 notification_count += 1
#             except Exception as e:
#                 # Log error but continue with other products
#                 _logger.error(f"Error sending notification for {orderpoint.product_id.name}: {str(e)}", exc_info=True)
#
#         _logger.info(f"=== Reorder check complete. Processed {notification_count} notifications ===")
#         return True
#
#     @api.model
#     def send_daily_summary(self):
#         """Send daily summary dashboard notification (No Email)"""
#         _logger.info("=== Starting daily summary ===")
#
#         # Get all orderpoints with notifications enabled
#         all_orderpoints = self.search([('notify_on_reorder', '=', True)])
#         low_stock_items = []
#
#         for op in all_orderpoints:
#             qty_on_hand = op._get_qty_on_hand()
#             if qty_on_hand <= op.product_min_qty:
#                 low_stock_items.append(op._get_reorder_details())
#
#         if not low_stock_items:
#             _logger.info("No low stock items found for daily summary")
#             return True
#
#         _logger.info(f"Found {len(low_stock_items)} low stock items")
#
#         # Get recipients
#         recipients = self.env['res.users']
#         purchase_group = self.env.ref('purchase.group_purchase_user', raise_if_not_found=False)
#         if purchase_group:
#             recipients |= purchase_group.users
#
#         stock_manager_group = self.env.ref('stock.group_stock_manager', raise_if_not_found=False)
#         if stock_manager_group:
#             recipients |= stock_manager_group.users
#
#         if not recipients:
#             _logger.warning("No recipients found for daily summary")
#             return True
#
#         # Create summary message for each user
#         for user in recipients:
#             # Build HTML summary
#             items_html = ""
#             for item in low_stock_items:
#                 items_html += f"""
#                 <div style="background-color: #f8f9fa; border-left: 4px solid #0066cc; padding: 12px; margin: 10px 0; border-radius: 5px;">
#                     <h4 style="color: #0066cc; margin: 0 0 8px 0;">{item['product_name']}</h4>
#                     <p style="margin: 3px 0; font-size: 13px; color: #666;">
#                         <strong>Code:</strong> {item['product_code']} |
#                         <strong>Warehouse:</strong> {item['warehouse']}
#                     </p>
#                     <div style="margin: 8px 0;">
#                         <span style="display: inline-block; background-color: #dc3545; color: white; padding: 4px 10px; border-radius: 3px; font-size: 12px; margin-right: 5px;">
#                             Current: {item['current_qty']} {item['uom']}
#                         </span>
#                         <span style="display: inline-block; background-color: #28a745; color: white; padding: 4px 10px; border-radius: 3px; font-size: 12px;">
#                             Order: {item['qty_to_order']} {item['uom']}
#                         </span>
#                     </div>
#                     <p style="margin: 3px 0; font-size: 13px; color: #495057;">
#                         <strong>Vendor:</strong> {item['vendor_name']} |
#                         <strong>Est. Cost:</strong> {item['currency']}{item['estimated_cost']:.2f}
#                     </p>
#                 </div>
#                 """
#
#             summary_body = f"""
#             <div style="font-family: Arial, sans-serif; padding: 20px; background-color: white; border-radius: 8px;">
#                 <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 8px; margin-bottom: 20px;">
#                     <h2 style="color: white; margin: 0; text-align: center;">📊 Daily Reorder Summary</h2>
#                     <p style="color: white; text-align: center; margin: 10px 0 0 0; font-size: 14px;">
#                         {fields.Date.today().strftime('%A, %B %d, %Y')}
#                     </p>
#                 </div>
#
#                 <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 20px; border-radius: 8px; margin-bottom: 20px; text-align: center; color: white;">
#                     <h1 style="margin: 0; font-size: 48px;">{len(low_stock_items)}</h1>
#                     <p style="margin: 5px 0 0 0; font-size: 16px;">Products Require Attention</p>
#                 </div>
#
#                 <h3 style="color: #495057; border-bottom: 2px solid #667eea; padding-bottom: 10px;">
#                     📦 Products Requiring Reorder
#                 </h3>
#
#                 {items_html}
#
#                 <div style="margin-top: 20px; padding-top: 15px; border-top: 2px solid #e9ecef; text-align: center; color: #6c757d; font-size: 12px;">
#                     <p>This is your automated daily summary from Odoo Inventory System</p>
#                     <p>Generated at: {fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
#                 </div>
#             </div>
#             """
#
#             # Send notification to user
#             try:
#                 user.partner_id.message_post(
#                     body=summary_body,
#                     subject=f'📊 Daily Reorder Summary - {len(low_stock_items)} Items Require Attention',
#                     message_type='notification',
#                     subtype_xmlid='mail.mt_note',
#                 )
#                 _logger.info(f"Daily summary sent to {user.name}")
#             except Exception as e:
#                 _logger.error(f"Error sending daily summary to {user.name}: {str(e)}")
#
#         _logger.info("=== Daily summary complete ===")
#         return True

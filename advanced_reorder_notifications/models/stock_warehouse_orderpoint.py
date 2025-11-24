from odoo import models, fields, api, _
from odoo.tools import format_datetime
from datetime import datetime


class StockWarehouseOrderpoint(models.Model):
    _inherit = 'stock.warehouse.orderpoint'

    notification_sent = fields.Boolean(string='Notification Sent', default=False)
    last_notification_date = fields.Datetime(string='Last Notification Date')
    notify_on_reorder = fields.Boolean(string='Send Notifications', default=True)

    def _get_qty_on_hand(self):
        """Get current quantity on hand"""
        self.ensure_one()
        return self.product_id.with_context(location=self.location_id.id).qty_available

    def _should_send_notification(self):
        """Check if notification should be sent"""
        self.ensure_one()
        qty_on_hand = self._get_qty_on_hand()

        # Check if below minimum and notification enabled
        if qty_on_hand <= self.product_min_qty and self.notify_on_reorder:
            # Allow re-notification after 24 hours
            if self.notification_sent and self.last_notification_date:
                from datetime import timedelta
                time_since_last = fields.Datetime.now() - self.last_notification_date
                if time_since_last < timedelta(hours=24):
                    return False  # Too soon, don't resend
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
        qty_to_order = self.product_max_qty - qty_on_hand

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
        warehouse = self.warehouse_id or self.location_id.warehouse_id

        # Get purchase users for this warehouse
        purchase_group = self.env.ref('purchase.group_purchase_user', raise_if_not_found=False)
        if purchase_group:
            recipients |= purchase_group.users

        # Get inventory managers
        stock_manager_group = self.env.ref('stock.group_stock_manager', raise_if_not_found=False)
        if stock_manager_group:
            recipients |= stock_manager_group.users

        # Get admins
        admin_group = self.env.ref('base.group_system', raise_if_not_found=False)
        if admin_group:
            # Only get admins if configured in settings
            get_param = self.env['ir.config_parameter'].sudo().get_param
            if get_param('reorder_notification.notify_admins', 'True') == 'True':
                recipients |= admin_group.users

        return recipients

    def send_reorder_notification(self):
        """Send notification for low stock - Dashboard Only (No Email)"""
        for orderpoint in self:
            if not orderpoint._should_send_notification():
                continue

            # Get reorder details
            details = orderpoint._get_reorder_details()
            recipients = orderpoint._get_notification_recipients()

            if not recipients:
                continue

            # Create activity/notification in Odoo Dashboard ONLY
            for user in recipients:
                # Check if activity already exists for this user
                existing_activity = self.env['mail.activity'].search([
                    ('res_id', '=', orderpoint.id),
                    ('res_model_id', '=', self.env.ref('stock.model_stock_warehouse_orderpoint').id),
                    ('user_id', '=', user.id),
                    ('activity_type_id', '=', self.env.ref('mail.mail_activity_data_todo').id),
                ], limit=1)

                if not existing_activity:
                    orderpoint.activity_schedule(
                        'mail.mail_activity_data_todo',
                        user_id=user.id,
                        summary=f'🔔 Reorder Required: {details["product_name"]}',
                        note=f"""
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
                                        <td style="padding: 10px; border: 1px solid #dee2e6; font-weight: bold;">Quantity to Order:</td>
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

                                <div style="text-align: center; margin-top: 15px;">
                                    <p style="color: #856404; font-size: 12px; margin: 0;">Click "Mark as Done" after creating the purchase order</p>
                                </div>
                            </div>
                        """
                    )

                    # Send internal message/notification (appears in chatter/inbox)
                    orderpoint.message_post(
                        body=f"""
                            <div style="padding: 10px; background-color: #fff3cd; border-left: 4px solid #ffc107;">
                                <strong>🔔 Reorder Notification Sent</strong><br/>
                                Notification sent to: {', '.join(recipients.mapped('name'))}<br/>
                                Product: {details['product_name']}<br/>
                                Current Stock: {details['current_qty']} {details['uom']} (Min: {details['min_qty']} {details['uom']})<br/>
                                Action Required: Order {details['qty_to_order']} {details['uom']}
                            </div>
                        """,
                        subject=f"Reorder Alert: {details['product_name']}",
                        message_type='notification',
                        subtype_xmlid='mail.mt_note',
                        partner_ids=recipients.mapped('partner_id').ids,
                    )

            # Update notification status
            orderpoint.write({
                'notification_sent': True,
                'last_notification_date': fields.Datetime.now(),
            })

    @api.model
    def check_all_reorder_rules(self):
        """Scheduled action to check all reordering rules"""
        # Get all active reordering rules
        orderpoints = self.search([
            ('notify_on_reorder', '=', True),
        ])

        # Check each orderpoint
        for orderpoint in orderpoints:
            try:
                orderpoint.send_reorder_notification()
            except Exception as e:
                # Log error but continue with other products
                _logger.error(f"Error sending notification for {orderpoint.product_id.name}: {str(e)}")

        return True

    @api.model
    def send_daily_summary(self):
        """Send daily summary dashboard notification (No Email)"""
        # Get all orderpoints below minimum
        low_stock_orderpoints = self.search([])
        low_stock_items = []

        for op in low_stock_orderpoints:
            qty_on_hand = op._get_qty_on_hand()
            if qty_on_hand <= op.product_min_qty:
                low_stock_items.append(op._get_reorder_details())

        if not low_stock_items:
            return True

        # Get recipients
        recipients = self.env['res.users']
        purchase_group = self.env.ref('purchase.group_purchase_user', raise_if_not_found=False)
        if purchase_group:
            recipients |= purchase_group.users

        stock_manager_group = self.env.ref('stock.group_stock_manager', raise_if_not_found=False)
        if stock_manager_group:
            recipients |= stock_manager_group.users

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

            # Post message to user (appears in Discuss/Inbox)
            self.env['mail.channel'].sudo().search([
                ('channel_type', '=', 'chat'),
                ('channel_partner_ids', 'in', user.partner_id.id)
            ], limit=1)

            # Create direct notification
            user.partner_id.message_post(
                body=summary_body,
                subject=f'📊 Daily Reorder Summary - {len(low_stock_items)} Items Require Attention',
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )

        return True











# from odoo import models, fields, api, _
# from odoo.tools import format_datetime
# from datetime import datetime
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
#         """Get current quantity on hand"""
#         self.ensure_one()
#         return self.product_id.with_context(location=self.location_id.id).qty_available
#
#     def _should_send_notification(self):
#         """Check if notification should be sent"""
#         self.ensure_one()
#         qty_on_hand = self._get_qty_on_hand()
#
#         # Check if below minimum and notification enabled
#         if qty_on_hand <= self.product_min_qty and self.notify_on_reorder:
#             return True
#         return False
#
#     def _get_reorder_details(self):
#         """Prepare detailed reorder information"""
#         self.ensure_one()
#
#         qty_on_hand = self._get_qty_on_hand()
#         qty_to_order = self.product_max_qty - qty_on_hand
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
#         warehouse = self.warehouse_id or self.location_id.warehouse_id
#
#         # Get purchase users for this warehouse
#         purchase_group = self.env.ref('purchase.group_purchase_user', raise_if_not_found=False)
#         if purchase_group:
#             recipients |= purchase_group.users
#
#         # Get inventory managers
#         stock_manager_group = self.env.ref('stock.group_stock_manager', raise_if_not_found=False)
#         if stock_manager_group:
#             recipients |= stock_manager_group.users
#
#         # Get admins
#         admin_group = self.env.ref('base.group_system', raise_if_not_found=False)
#         if admin_group:
#             # Only get admins if configured in settings
#             get_param = self.env['ir.config_parameter'].sudo().get_param
#             if get_param('reorder_notification.notify_admins', 'True') == 'True':
#                 recipients |= admin_group.users
#
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
#                 continue
#
#             # Create activity/notification in Odoo Dashboard ONLY
#             for user in recipients:
#                 # Check if activity already exists for this user
#                 existing_activity = self.env['mail.activity'].search([
#                     ('res_id', '=', orderpoint.id),
#                     ('res_model_id', '=', self.env.ref('stock.model_stock_warehouse_orderpoint').id),
#                     ('user_id', '=', user.id),
#                     ('activity_type_id', '=', self.env.ref('mail.mail_activity_data_todo').id),
#                 ], limit=1)
#
#                 if not existing_activity:
#                     orderpoint.activity_schedule(
#                         'mail.mail_activity_data_todo',
#                         user_id=user.id,
#                         summary=f'🔔 Reorder Required: {details["product_name"]}',
#                         note=f"""
#                             <div style="font-family: Arial, sans-serif; padding: 15px; background-color: #fff3cd; border-left: 4px solid #ffc107; border-radius: 5px;">
#                                 <h3 style="color: #856404; margin-top: 0;">⚠️ Low Stock Alert</h3>
#
#                                 <div style="background-color: white; padding: 15px; border-radius: 5px; margin: 10px 0;">
#                                     <h4 style="color: #0066cc; margin: 0 0 10px 0;">{details['product_name']}</h4>
#                                     <p style="margin: 5px 0; color: #666;"><strong>Product Code:</strong> {details['product_code']}</p>
#                                 </div>
#
#                                 <table style="width: 100%; border-collapse: collapse; margin: 15px 0; background-color: white;">
#                                     <tr style="background-color: #f8f9fa;">
#                                         <td style="padding: 10px; border: 1px solid #dee2e6; font-weight: bold;">Current Stock:</td>
#                                         <td style="padding: 10px; border: 1px solid #dee2e6; color: #dc3545; font-weight: bold; font-size: 16px;">
#                                             {details['current_qty']} {details['uom']}
#                                         </td>
#                                     </tr>
#                                     <tr>
#                                         <td style="padding: 10px; border: 1px solid #dee2e6; font-weight: bold;">Minimum Required:</td>
#                                         <td style="padding: 10px; border: 1px solid #dee2e6;">{details['min_qty']} {details['uom']}</td>
#                                     </tr>
#                                     <tr style="background-color: #f8f9fa;">
#                                         <td style="padding: 10px; border: 1px solid #dee2e6; font-weight: bold;">Maximum Level:</td>
#                                         <td style="padding: 10px; border: 1px solid #dee2e6;">{details['max_qty']} {details['uom']}</td>
#                                     </tr>
#                                     <tr style="background-color: #d4edda;">
#                                         <td style="padding: 10px; border: 1px solid #dee2e6; font-weight: bold;">Quantity to Order:</td>
#                                         <td style="padding: 10px; border: 1px solid #dee2e6; color: #155724; font-weight: bold; font-size: 16px;">
#                                             {details['qty_to_order']} {details['uom']}
#                                         </td>
#                                     </tr>
#                                 </table>
#
#                                 <div style="background-color: white; padding: 15px; border-radius: 5px; margin: 10px 0;">
#                                     <h4 style="color: #495057; margin: 0 0 10px 0;">📍 Location & Vendor Details</h4>
#                                     <p style="margin: 5px 0;"><strong>Warehouse:</strong> {details['warehouse']}</p>
#                                     <p style="margin: 5px 0;"><strong>Location:</strong> {details['location']}</p>
#                                     <p style="margin: 5px 0;"><strong>Vendor:</strong> {details['vendor_name']}</p>
#                                     <p style="margin: 5px 0;"><strong>Unit Price:</strong> {details['currency']}{details['vendor_price']:.2f}</p>
#                                     <p style="margin: 5px 0;"><strong>Estimated Cost:</strong> <span style="color: #28a745; font-weight: bold;">{details['currency']}{details['estimated_cost']:.2f}</span></p>
#                                     <p style="margin: 5px 0;"><strong>Lead Time:</strong> {details['lead_time']} days</p>
#                                 </div>
#
#                                 <div style="text-align: center; margin-top: 15px;">
#                                     <p style="color: #856404; font-size: 12px; margin: 0;">Click "Mark as Done" after creating the purchase order</p>
#                                 </div>
#                             </div>
#                         """
#                     )
#
#                     # Send internal message/notification (appears in chatter/inbox)
#                     orderpoint.message_post(
#                         body=f"""
#                             <div style="padding: 10px; background-color: #fff3cd; border-left: 4px solid #ffc107;">
#                                 <strong>🔔 Reorder Notification Sent</strong><br/>
#                                 Notification sent to: {', '.join(recipients.mapped('name'))}<br/>
#                                 Product: {details['product_name']}<br/>
#                                 Current Stock: {details['current_qty']} {details['uom']} (Min: {details['min_qty']} {details['uom']})<br/>
#                                 Action Required: Order {details['qty_to_order']} {details['uom']}
#                             </div>
#                         """,
#                         subject=f"Reorder Alert: {details['product_name']}",
#                         message_type='notification',
#                         subtype_xmlid='mail.mt_note',
#                         partner_ids=recipients.mapped('partner_id').ids,
#                     )
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
#         # Get all active reordering rules
#         orderpoints = self.search([
#             ('notify_on_reorder', '=', True),
#         ])
#
#         # Check each orderpoint
#         for orderpoint in orderpoints:
#             try:
#                 orderpoint.send_reorder_notification()
#             except Exception as e:
#                 # Log error but continue with other products
#                 _logger.error(f"Error sending notification for {orderpoint.product_id.name}: {str(e)}")
#
#         return True
#
#     @api.model
#     def send_daily_summary(self):
#         """Send daily summary dashboard notification (No Email)"""
#         # Get all orderpoints below minimum
#         low_stock_orderpoints = self.search([])
#         low_stock_items = []
#
#         for op in low_stock_orderpoints:
#             qty_on_hand = op._get_qty_on_hand()
#             if qty_on_hand <= op.product_min_qty:
#                 low_stock_items.append(op._get_reorder_details())
#
#         if not low_stock_items:
#             return True
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
#             # Post message to user (appears in Discuss/Inbox)
#             self.env['mail.channel'].sudo().search([
#                 ('channel_type', '=', 'chat'),
#                 ('channel_partner_ids', 'in', user.partner_id.id)
#             ], limit=1)
#
#             # Create direct notification
#             user.partner_id.message_post(
#                 body=summary_body,
#                 subject=f'📊 Daily Reorder Summary - {len(low_stock_items)} Items Require Attention',
#                 message_type='notification',
#                 subtype_xmlid='mail.mt_note',
#             )
#
#         return True
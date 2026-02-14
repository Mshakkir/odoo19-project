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

    has_active_notification = fields.Boolean(
        string='Has Active Notification',
        compute='_compute_has_active_notification',
        store=False,
        help='Whether this orderpoint has active notifications'
    )

    stock_status = fields.Selection([
        ('ok', 'Stock OK'),
        ('below_min', 'Below Minimum'),
        ('above_max', 'Above Maximum'),
    ], string='Stock Status', compute='_compute_stock_status', store=False)

    @api.depends('product_id', 'location_id')
    def _compute_has_active_notification(self):
        """Check if orderpoint has active notifications"""
        for rec in self:
            activity_type = self.env.ref(
                'warehouse_reorder_notification.mail_activity_type_reorder_notification',
                raise_if_not_found=False
            )

            if activity_type:
                active_count = self.env['mail.activity'].sudo().search_count([
                    ('res_id', '=', rec.id),
                    ('res_model', '=', 'stock.warehouse.orderpoint'),
                    ('activity_type_id', '=', activity_type.id),
                ])
                rec.has_active_notification = active_count > 0
            else:
                rec.has_active_notification = False

    @api.depends('product_id', 'location_id', 'product_min_qty', 'product_max_qty')
    def _compute_stock_status(self):
        """Compute current stock status"""
        for rec in self:
            if not rec.product_id or not rec.location_id:
                rec.stock_status = 'ok'
                continue

            qty_available = rec.product_id.with_context(
                location=rec.location_id.id
            ).qty_available

            if qty_available < rec.product_min_qty:
                rec.stock_status = 'below_min'
            elif qty_available > rec.product_max_qty:
                rec.stock_status = 'above_max'
            else:
                rec.stock_status = 'ok'

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

        # Create notification title with CLEAR warehouse name
        notification_icon = '🔴' if notification_data['notification_type'] == 'below_min' else '🟡'
        title = f"{notification_icon} [{notification_data['warehouse_name']}] {notification_data['product_name']}"

        # Create notification message
        message_body = self._format_notification_message_simple(notification_data)

        # Get custom activity type - THIS IS CRITICAL
        activity_type = self.env.ref(
            'warehouse_reorder_notification.mail_activity_type_reorder_notification',
            raise_if_not_found=False
        )

        if not activity_type:
            # Fallback to todo if custom type not found
            activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)

        if not activity_type:
            return False

        # Send notification ONLY to users assigned to THIS warehouse
        for user in users_to_notify:
            try:
                # Check if activity already exists for this user/orderpoint
                existing_activity = self.env['mail.activity'].sudo().search([
                    ('res_id', '=', self.id),
                    ('res_model', '=', 'stock.warehouse.orderpoint'),
                    ('user_id', '=', user.id),
                    ('activity_type_id', '=', activity_type.id),
                ], limit=1)

                if existing_activity:
                    # Update existing activity
                    existing_activity.sudo().write({
                        'summary': title,
                        'note': message_body,
                        'date_deadline': fields.Date.today(),
                    })
                else:
                    # Create NEW activity
                    new_activity = self.env['mail.activity'].sudo().create({
                        'activity_type_id': activity_type.id,
                        'summary': title,
                        'note': message_body,
                        'res_id': self.id,
                        'res_model_id': self.env['ir.model']._get_id('stock.warehouse.orderpoint'),
                        'user_id': user.id,
                        'date_deadline': fields.Date.today(),
                    })

                    # CRITICAL: Recompute warehouse_id for this activity
                    new_activity._compute_warehouse_id()

                    # Send browser notification using Odoo 19 bus system
                    # The activity creation itself triggers the notification
                    # No need for manual bus.bus calls in Odoo 19
                    pass

            except Exception as e:
                continue

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

    def _auto_close_notifications_if_stock_ok(self):
        """Close notifications if stock is now within acceptable range"""
        self.ensure_one()

        try:
            product = self.product_id
            location = self.location_id

            if not product or not location:
                return

            # Get current stock with proper context
            qty_available = product.with_context(location=location.id).qty_available

            # Check if stock is now OK (within min-max range)
            if qty_available >= self.product_min_qty and qty_available <= self.product_max_qty:
                # Get activity type
                activity_type = self.env.ref(
                    'warehouse_reorder_notification.mail_activity_type_reorder_notification',
                    raise_if_not_found=False
                )

                if activity_type:
                    # Find and mark all activities as done
                    activities = self.env['mail.activity'].sudo().search([
                        ('res_id', '=', self.id),
                        ('res_model', '=', 'stock.warehouse.orderpoint'),
                        ('activity_type_id', '=', activity_type.id),
                    ])

                    for activity in activities:
                        try:
                            activity.action_done()
                        except:
                            pass

        except Exception as e:
            pass

    def action_check_and_notify(self):
        """Manual action to check stock and send notifications if needed"""
        self.ensure_one()

        product = self.product_id
        location = self.location_id

        if not product or not location:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Configuration Error'),
                    'message': _('Product or location not properly configured'),
                    'type': 'warning',
                    'sticky': False,
                }
            }

        qty_available = product.with_context(location=location.id).qty_available

        # Check if below minimum
        if qty_available < self.product_min_qty:
            notification_data = {
                'product_name': product.name,
                'product_code': product.default_code or '',
                'warehouse_name': self.warehouse_id.name if self.warehouse_id else 'N/A',
                'location_name': location.complete_name or location.name,
                'qty_available': qty_available,
                'product_min_qty': self.product_min_qty,
                'product_max_qty': self.product_max_qty,
                'product_uom': product.uom_id.name,
                'notification_type': 'below_min',
                'message': f'Stock is below minimum! Current: {qty_available:.2f}, Min: {self.product_min_qty:.2f}',
            }

            self._send_system_notification(notification_data)

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('✅ Notification Sent'),
                    'message': _('Reorder notification sent successfully to warehouse users'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Stock OK'),
                    'message': _('Current stock (%.2f) is above minimum (%.2f). No notification needed.') % (
                        qty_available, self.product_min_qty),
                    'type': 'info',
                    'sticky': False,
                }
            }

    def _cron_check_stock_levels(self):
        """Scheduled action to check all orderpoints and send notifications"""
        orderpoints = self.search([
            ('warehouse_id.enable_reorder_notifications', '=', True),
        ])

        for orderpoint in orderpoints:
            try:
                product = orderpoint.product_id
                location = orderpoint.location_id

                if not product or not location:
                    continue

                qty_available = product.with_context(location=location.id).qty_available

                # First, check if stock is now OK and close notifications if needed
                if qty_available >= orderpoint.product_min_qty:
                    orderpoint._auto_close_notifications_if_stock_ok()
                    continue

                # Stock is below minimum - send/update notification
                notification_data = {
                    'product_name': product.name,
                    'product_code': product.default_code or '',
                    'warehouse_name': orderpoint.warehouse_id.name if orderpoint.warehouse_id else 'N/A',
                    'location_name': location.complete_name or location.name,
                    'qty_available': qty_available,
                    'product_min_qty': orderpoint.product_min_qty,
                    'product_max_qty': orderpoint.product_max_qty,
                    'product_uom': product.uom_id.name,
                    'notification_type': 'below_min',
                    'message': f'Stock is below minimum! Current: {qty_available:.2f}, Min: {orderpoint.product_min_qty:.2f}',
                }

                orderpoint._send_system_notification(notification_data)

                # Update notification tracking
                orderpoint.sudo().write({
                    'last_notification_date': fields.Datetime.now(),
                    'notification_count': orderpoint.notification_count + 1,
                })

            except Exception as e:
                continue

    def action_create_purchase_order(self):
        """Create a draft purchase order for this reordering rule

        SOLUTION: Use sudo() to create PO, but immediately share it with current user
        via message_subscribe so they can see it despite record rules.
        """
        self.ensure_one()

        # Check if stock is below minimum
        product = self.product_id
        location = self.location_id
        qty_available = product.with_context(location=location.id).qty_available

        if qty_available >= self.product_min_qty:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Replenishment Needed'),
                    'message': _('Current stock (%.2f) is above minimum (%.2f)') % (
                        qty_available, self.product_min_qty),
                    'type': 'info',
                    'sticky': False,
                }
            }

        # Calculate quantity to order
        qty_to_order = self.product_max_qty - qty_available

        if qty_to_order <= 0:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Invalid Quantity'),
                    'message': _('Cannot calculate order quantity'),
                    'type': 'warning',
                    'sticky': False,
                }
            }

        # Get vendor
        vendor = False
        price = 0.0
        if product.seller_ids:
            vendor = product.seller_ids[0].partner_id
            price = product.seller_ids[0].price

        if not vendor:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Vendor'),
                    'message': _('Please configure a vendor for product %s') % product.name,
                    'type': 'warning',
                    'sticky': False,
                }
            }

        # Create purchase order in DRAFT state
        try:
            warehouse = self.warehouse_id
            current_user = self.env.user

            # Create PO with sudo() to bypass record rules
            po_vals = {
                'partner_id': vendor.id,
                'date_order': fields.Datetime.now(),
                'origin': f'Reorder: {self.name}',
                'picking_type_id': warehouse.in_type_id.id if warehouse else False,
                'state': 'draft',
            }

            purchase_order = self.env['purchase.order'].sudo().create(po_vals)

            # Create purchase order line
            line_vals = {
                'order_id': purchase_order.id,
                'product_id': product.id,
                'product_qty': qty_to_order,
                'product_uom_id': product.uom_id.id,
                'price_unit': price,
                'date_planned': fields.Datetime.now(),
                'name': product.display_name,
            }

            self.env['purchase.order.line'].sudo().create(line_vals)

            # CRITICAL FIX: Subscribe current user as follower so they can access the PO
            # This bypasses record rule restrictions
            purchase_order.sudo().message_subscribe(partner_ids=[current_user.partner_id.id])

            # Close the notification activity for this user
            activity_type = self.env.ref(
                'warehouse_reorder_notification.mail_activity_type_reorder_notification',
                raise_if_not_found=False
            )

            if activity_type:
                # Find user's activity for this orderpoint
                user_activity = self.env['mail.activity'].search([
                    ('res_id', '=', self.id),
                    ('res_model', '=', 'stock.warehouse.orderpoint'),
                    ('user_id', '=', self.env.user.id),
                    ('activity_type_id', '=', activity_type.id),
                ], limit=1)

                if user_activity:
                    try:
                        user_activity.action_done()
                    except:
                        pass

            # Return action to open the PO form
            # User can now access because they're a follower
            return {
                'type': 'ir.actions.act_window',
                'name': _('Purchase Order (Draft)'),
                'res_model': 'purchase.order',
                'res_id': purchase_order.id,
                'view_mode': 'form',
                'target': 'current',
            }

        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _('Error creating purchase order: %s') % str(e),
                    'type': 'danger',
                    'sticky': False,
                }
            }

    def action_create_combined_purchase_order(self):
        """Create ONE combined purchase order for ALL selected products"""
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

        orderpoints_data = []
        default_vendor = False

        for orderpoint in self:
            product = orderpoint.product_id
            location = orderpoint.location_id
            qty_available = product.with_context(location=location.id).qty_available

            if qty_available < orderpoint.product_min_qty:
                qty_to_order = orderpoint.product_max_qty - qty_available

                if qty_to_order > 0:
                    vendor = False
                    price = 0.0

                    if product.seller_ids:
                        vendor = product.seller_ids[0].partner_id
                        price = product.seller_ids[0].price

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

        warehouse = self[0].warehouse_id
        current_user = self.env.user

        po_vals = {
            'date_order': fields.Datetime.now(),
            'origin': f'Combined Reorder - {warehouse.name}',
            'picking_type_id': warehouse.in_type_id.id,
            'state': 'draft',
        }

        if default_vendor:
            po_vals['partner_id'] = default_vendor.id

        purchase_order = self.env['purchase.order'].sudo().create(po_vals)

        for op_data in orderpoints_data:
            product = op_data['product']
            qty = op_data['qty_to_order']
            price = op_data['price']

            line_vals = {
                'order_id': purchase_order.id,
                'product_id': product.id,
                'product_qty': qty,
                'product_uom_id': product.uom_id.id,
                'price_unit': price,
                'date_planned': fields.Datetime.now(),
                'name': product.display_name,
            }

            self.env['purchase.order.line'].sudo().create(line_vals)

        # Subscribe current user as follower
        purchase_order.sudo().message_subscribe(partner_ids=[current_user.partner_id.id])

        return {
            'type': 'ir.actions.act_window',
            'name': _('Combined Purchase Order (Draft)'),
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
#     has_active_notification = fields.Boolean(
#         string='Has Active Notification',
#         compute='_compute_has_active_notification',
#         store=False,
#         help='Whether this orderpoint has active notifications'
#     )
#
#     stock_status = fields.Selection([
#         ('ok', 'Stock OK'),
#         ('below_min', 'Below Minimum'),
#         ('above_max', 'Above Maximum'),
#     ], string='Stock Status', compute='_compute_stock_status', store=False)
#
#     @api.depends('product_id', 'location_id')
#     def _compute_has_active_notification(self):
#         """Check if orderpoint has active notifications"""
#         for rec in self:
#             activity_type = self.env.ref(
#                 'warehouse_reorder_notification.mail_activity_type_reorder_notification',
#                 raise_if_not_found=False
#             )
#
#             if activity_type:
#                 active_count = self.env['mail.activity'].sudo().search_count([
#                     ('res_id', '=', rec.id),
#                     ('res_model', '=', 'stock.warehouse.orderpoint'),
#                     ('activity_type_id', '=', activity_type.id),
#                 ])
#                 rec.has_active_notification = active_count > 0
#             else:
#                 rec.has_active_notification = False
#
#     @api.depends('product_id', 'location_id', 'product_min_qty', 'product_max_qty')
#     def _compute_stock_status(self):
#         """Compute current stock status"""
#         for rec in self:
#             if not rec.product_id or not rec.location_id:
#                 rec.stock_status = 'ok'
#                 continue
#
#             qty_available = rec.product_id.with_context(
#                 location=rec.location_id.id
#             ).qty_available
#
#             if qty_available < rec.product_min_qty:
#                 rec.stock_status = 'below_min'
#             elif qty_available > rec.product_max_qty:
#                 rec.stock_status = 'above_max'
#             else:
#                 rec.stock_status = 'ok'
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
#         # Create notification title with CLEAR warehouse name
#         notification_icon = '🔴' if notification_data['notification_type'] == 'below_min' else '🟡'
#         title = f"{notification_icon} [{notification_data['warehouse_name']}] {notification_data['product_name']}"
#
#         # Create notification message
#         message_body = self._format_notification_message_simple(notification_data)
#
#         # Get custom activity type - THIS IS CRITICAL
#         activity_type = self.env.ref(
#             'warehouse_reorder_notification.mail_activity_type_reorder_notification',
#             raise_if_not_found=False
#         )
#
#         if not activity_type:
#             # Fallback to todo if custom type not found
#             activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
#
#         if not activity_type:
#             return False
#
#         # Send notification ONLY to users assigned to THIS warehouse
#         for user in users_to_notify:
#             try:
#                 # Check if activity already exists for this user/orderpoint
#                 existing_activity = self.env['mail.activity'].sudo().search([
#                     ('res_id', '=', self.id),
#                     ('res_model', '=', 'stock.warehouse.orderpoint'),
#                     ('user_id', '=', user.id),
#                     ('activity_type_id', '=', activity_type.id),
#                 ], limit=1)
#
#                 if existing_activity:
#                     # Update existing activity
#                     existing_activity.sudo().write({
#                         'summary': title,
#                         'note': message_body,
#                         'date_deadline': fields.Date.today(),
#                     })
#                 else:
#                     # Create NEW activity
#                     new_activity = self.env['mail.activity'].sudo().create({
#                         'activity_type_id': activity_type.id,
#                         'summary': title,
#                         'note': message_body,
#                         'res_id': self.id,
#                         'res_model_id': self.env['ir.model']._get_id('stock.warehouse.orderpoint'),
#                         'user_id': user.id,
#                         'date_deadline': fields.Date.today(),
#                     })
#
#                     # CRITICAL: Recompute warehouse_id for this activity
#                     new_activity._compute_warehouse_id()
#
#                     # Send browser notification using Odoo 19 bus system
#                     # The activity creation itself triggers the notification
#                     # No need for manual bus.bus calls in Odoo 19
#                     pass
#
#             except Exception as e:
#                 continue
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
#     def _auto_close_notifications_if_stock_ok(self):
#         """Close notifications if stock is now within acceptable range"""
#         self.ensure_one()
#
#         try:
#             product = self.product_id
#             location = self.location_id
#
#             if not product or not location:
#                 return
#
#             # Get current stock with proper context
#             qty_available = product.with_context(
#                 location=location.id,
#                 compute_child=False
#             ).qty_available
#
#             # If stock is now within acceptable range, close activities
#             if self.product_min_qty <= qty_available <= self.product_max_qty:
#                 # Get custom activity type
#                 activity_type = self.env.ref(
#                     'warehouse_reorder_notification.mail_activity_type_reorder_notification',
#                     raise_if_not_found=False
#                 )
#
#                 # Build domain for activities to close
#                 domain = [
#                     ('res_id', '=', self.id),
#                     ('res_model', '=', 'stock.warehouse.orderpoint'),
#                 ]
#
#                 if activity_type:
#                     domain.append(('activity_type_id', '=', activity_type.id))
#
#                 # Find and close activities
#                 open_activities = self.env['mail.activity'].sudo().search(domain)
#
#                 if open_activities:
#                     for activity in open_activities:
#                         try:
#                             # Mark as done (creates message in chatter)
#                             activity.action_done()
#                         except:
#                             # If action_done fails, just delete
#                             activity.unlink()
#
#                     # Log that notifications were auto-closed
#                     self.message_post(
#                         body=f"✅ Stock replenished to {qty_available:.2f} {product.uom_id.name}. "
#                              f"Reorder notifications automatically closed.",
#                         subject="Stock Replenished"
#                     )
#         except Exception as e:
#             # Log error but don't break the flow
#             pass
#
#     @api.model
#     def check_and_send_reorder_notifications(self):
#         """Check all reordering rules and send notifications (Called by cron)"""
#         # Get all warehouses with notifications enabled
#         warehouses = self.env['stock.warehouse'].sudo().search([
#             ('enable_reorder_notifications', '=', True)
#         ])
#
#         notifications_sent = 0
#         notifications_closed = 0
#
#         # Process each warehouse separately
#         for warehouse in warehouses:
#             # Get users for THIS specific warehouse
#             warehouse_users = warehouse.sudo()._get_notification_users()
#
#             if not warehouse_users:
#                 continue
#
#             # Get orderpoints ONLY for this warehouse
#             orderpoints = self.sudo().search([
#                 ('warehouse_id', '=', warehouse.id),
#                 ('warehouse_id.enable_reorder_notifications', '=', True)
#             ])
#
#             for orderpoint in orderpoints:
#                 try:
#                     product = orderpoint.product_id
#                     location = orderpoint.location_id
#
#                     # Get on-hand quantity
#                     qty_available = product.with_context(location=location.id).qty_available
#
#                     # Auto-close notifications if stock is OK
#                     if orderpoint.product_min_qty <= qty_available <= orderpoint.product_max_qty:
#                         # Check if there are open notifications before closing
#                         activity_type = self.env.ref(
#                             'warehouse_reorder_notification.mail_activity_type_reorder_notification',
#                             raise_if_not_found=False
#                         )
#
#                         if activity_type:
#                             open_count = self.env['mail.activity'].sudo().search_count([
#                                 ('res_id', '=', orderpoint.id),
#                                 ('res_model', '=', 'stock.warehouse.orderpoint'),
#                                 ('activity_type_id', '=', activity_type.id),
#                             ])
#
#                             if open_count > 0:
#                                 orderpoint._auto_close_notifications_if_stock_ok()
#                                 notifications_closed += 1
#
#                         continue
#
#                     # Skip if notification was sent in last 4 hours
#                     if orderpoint.last_notification_date:
#                         time_diff = datetime.now() - orderpoint.last_notification_date
#                         if time_diff < timedelta(hours=4):
#                             continue
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
#                     # Send notification if needed
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
#                     continue
#
#         return {
#             'sent': notifications_sent,
#             'closed': notifications_closed
#         }
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
#     def action_close_notification(self):
#         """Manual button to close notification"""
#         self.ensure_one()
#         self._auto_close_notifications_if_stock_ok()
#
#         return {
#             'type': 'ir.actions.client',
#             'tag': 'display_notification',
#             'params': {
#                 'title': _('✅ Closed'),
#                 'message': _('Notification closed successfully.'),
#                 'type': 'success',
#                 'sticky': False,
#             }
#         }
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
#
#     def action_replenish(self):
#         """Override standard Odoo replenish action to create purchase order"""
#         self.ensure_one()
#
#         # Check if stock is below minimum
#         product = self.product_id
#         location = self.location_id
#         qty_available = product.with_context(location=location.id).qty_available
#
#         if qty_available >= self.product_min_qty:
#             return {
#                 'type': 'ir.actions.client',
#                 'tag': 'display_notification',
#                 'params': {
#                     'title': _('No Replenishment Needed'),
#                     'message': _('Current stock (%.2f) is above minimum (%.2f)') % (
#                         qty_available, self.product_min_qty),
#                     'type': 'info',
#                     'sticky': False,
#                 }
#             }
#
#         # Calculate quantity to order
#         qty_to_order = self.product_max_qty - qty_available
#
#         if qty_to_order <= 0:
#             return {
#                 'type': 'ir.actions.client',
#                 'tag': 'display_notification',
#                 'params': {
#                     'title': _('Invalid Quantity'),
#                     'message': _('Cannot calculate order quantity'),
#                     'type': 'warning',
#                     'sticky': False,
#                 }
#             }
#
#         # Get vendor
#         vendor = False
#         price = 0.0
#         if product.seller_ids:
#             vendor = product.seller_ids[0].partner_id
#             price = product.seller_ids[0].price
#
#         if not vendor:
#             return {
#                 'type': 'ir.actions.client',
#                 'tag': 'display_notification',
#                 'params': {
#                     'title': _('No Vendor'),
#                     'message': _('Please configure a vendor for product %s') % product.name,
#                     'type': 'warning',
#                     'sticky': False,
#                 }
#             }
#
#         # Create purchase order
#         try:
#             warehouse = self.warehouse_id
#
#             po_vals = {
#                 'partner_id': vendor.id,
#                 'date_order': fields.Datetime.now(),
#                 'origin': f'Reorder: {self.name}',
#                 'picking_type_id': warehouse.in_type_id.id if warehouse else False,
#             }
#
#             purchase_order = self.env['purchase.order'].sudo().create(po_vals)
#
#             # Create purchase order line
#             line_vals = {
#                 'order_id': purchase_order.id,
#                 'product_id': product.id,
#                 'product_qty': qty_to_order,
#                 'product_uom_id': product.uom_id.id,
#                 'price_unit': price,
#                 'date_planned': fields.Datetime.now(),
#                 'name': product.display_name,
#             }
#
#             self.env['purchase.order.line'].sudo().create(line_vals)
#
#             # Return success notification (user can view PO in Purchase menu)
#             return {
#                 'type': 'ir.actions.client',
#                 'tag': 'display_notification',
#                 'params': {
#                     'title': _('✅ Purchase Order Created'),
#                     'message': _(
#                         'PO %s created successfully. Go to Purchase → Orders to view it.') % purchase_order.name,
#                     'type': 'success',
#                     'sticky': True,
#                 }
#             }
#
#         except Exception as e:
#             return {
#                 'type': 'ir.actions.client',
#                 'tag': 'display_notification',
#                 'params': {
#                     'title': _('Error'),
#                     'message': _('Error creating purchase order: %s') % str(e),
#                     'type': 'danger',
#                     'sticky': False,
#                 }
#             }
#
#     def action_create_combined_purchase_order(self):
#         """Create ONE combined purchase order for ALL selected products"""
#         if not self:
#             return {
#                 'type': 'ir.actions.client',
#                 'tag': 'display_notification',
#                 'params': {
#                     'title': _('No Records Selected'),
#                     'message': _('Please select at least one reordering rule.'),
#                     'type': 'warning',
#                     'sticky': False,
#                 }
#             }
#
#         orderpoints_data = []
#         default_vendor = False
#
#         for orderpoint in self:
#             product = orderpoint.product_id
#             location = orderpoint.location_id
#             qty_available = product.with_context(location=location.id).qty_available
#
#             if qty_available < orderpoint.product_min_qty:
#                 qty_to_order = orderpoint.product_max_qty - qty_available
#
#                 if qty_to_order > 0:
#                     vendor = False
#                     price = 0.0
#
#                     if product.seller_ids:
#                         vendor = product.seller_ids[0].partner_id
#                         price = product.seller_ids[0].price
#
#                         if not default_vendor:
#                             default_vendor = vendor
#
#                     orderpoints_data.append({
#                         'orderpoint': orderpoint,
#                         'product': product,
#                         'qty_to_order': qty_to_order,
#                         'vendor': vendor,
#                         'price': price,
#                     })
#
#         if not orderpoints_data:
#             return {
#                 'type': 'ir.actions.client',
#                 'tag': 'display_notification',
#                 'params': {
#                     'title': _('No Orders Needed'),
#                     'message': _('All selected products have sufficient stock or are above minimum quantity.'),
#                     'type': 'info',
#                     'sticky': False,
#                 }
#             }
#
#         warehouse = self[0].warehouse_id
#
#         po_vals = {
#             'date_order': fields.Datetime.now(),
#             'origin': f'Combined Reorder - {warehouse.name}',
#             'picking_type_id': warehouse.in_type_id.id,
#         }
#
#         if default_vendor:
#             po_vals['partner_id'] = default_vendor.id
#
#         purchase_order = self.env['purchase.order'].sudo().create(po_vals)
#
#         for op_data in orderpoints_data:
#             product = op_data['product']
#             qty = op_data['qty_to_order']
#             price = op_data['price']
#
#             line_vals = {
#                 'order_id': purchase_order.id,
#                 'product_id': product.id,
#                 'product_qty': qty,
#                 'product_uom_id': product.uom_id.id,
#                 'price_unit': price,
#                 'date_planned': fields.Datetime.now(),
#                 'name': product.display_name,
#             }
#
#             self.env['purchase.order.line'].sudo().create(line_vals)
#
#         return {
#             'type': 'ir.actions.act_window',
#             'name': _('Combined Purchase Order Created'),
#             'res_model': 'purchase.order',
#             'res_id': purchase_order.id,
#             'view_mode': 'form',
#             'target': 'current',
#         }
#
#
#
#

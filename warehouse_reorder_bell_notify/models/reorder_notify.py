from odoo import models, api, _
from odoo.exceptions import UserError


class ReorderRuleNotification(models.Model):
    _inherit = 'stock.warehouse.orderpoint'

    # ------------------------------------------
    # GET USER ALLOWED WAREHOUSES
    # ------------------------------------------
    def _get_user_warehouses(self, user):
        """Get warehouses assigned to user"""
        if hasattr(user, 'stock_warehouse_ids') and user.stock_warehouse_ids:
            return user.stock_warehouse_ids
        return self.env['stock.warehouse'].browse()  # Empty recordset

    # ------------------------------------------
    # CHECK IF USER IS ADMIN
    # ------------------------------------------
    def _is_admin(self, user):
        """Check if user is system administrator"""
        return user.has_group('base.group_system')

    # ------------------------------------------
    # SEND NOTIFICATION TO USER
    # ------------------------------------------
    def _send_notification(self, user, message):
        """Send notification using Odoo's bus notification system"""
        try:
            self.env['bus.bus']._sendone(
                user.partner_id,
                'simple_notification',
                {
                    'type': 'info',
                    'title': _('Reorder Alert'),
                    'message': message,
                    'sticky': False,
                }
            )
        except Exception as e:
            # Log error but don't break the flow
            print(f"Notification error for user {user.name}: {str(e)}")

    # ------------------------------------------
    # AUTO - NOTIFICATION (CRON)
    # ------------------------------------------
    @api.model
    def cron_send_reorder_notifications(self):
        """Send automatic reorder notifications"""

        # Get all reorder rules that need attention
        all_rules = self.search([
            ('qty_to_order', '>', 0),
            ('product_id', '!=', False),
        ])

        if not all_rules:
            return

        # Get all active users
        all_users = self.env['res.users'].search([('active', '=', True)])

        notified_users = 0

        for user in all_users:
            is_admin = self._is_admin(user)

            if is_admin:
                # ADMIN: Get ALL reorder rules from ALL warehouses
                user_rules = all_rules
            else:
                # REGULAR USER: Get only rules from assigned warehouses
                user_warehouses = self._get_user_warehouses(user)

                if not user_warehouses:
                    continue  # Skip users without warehouse assignment

                user_rules = all_rules.filtered(
                    lambda r: r.warehouse_id in user_warehouses
                )

            if not user_rules:
                continue

            # Build notification message
            product_lines = []
            for rule in user_rules:
                warehouse_name = rule.warehouse_id.name or 'Unknown'
                product_lines.append(
                    f"• [{warehouse_name}] {rule.product_id.display_name}: "
                    f"Need {rule.qty_to_order} {rule.product_uom.name}"
                )

            if is_admin:
                title = _("📦 Admin Alert - All Warehouses")
                footer = _("\n\n✓ You are receiving all warehouse alerts as administrator.")
            else:
                warehouse_names = ', '.join(user_rules.mapped('warehouse_id.name'))
                title = _("📦 Reorder Alert - Your Warehouses")
                footer = _("\n\n✓ Showing only: %s") % warehouse_names

            message = f"{title}\n\n" + "\n".join(product_lines) + footer

            self._send_notification(user, message)
            notified_users += 1

        print(f"Reorder notifications sent to {notified_users} user(s)")

    # -----------------------------------------
    # MANUAL BUTTON NOTIFICATION
    # -----------------------------------------
    def action_manual_reorder_notify(self):
        """Manual trigger for reorder notifications"""

        # Get all reorder rules that need attention
        all_rules = self.search([
            ('qty_to_order', '>', 0),
            ('product_id', '!=', False)
        ])

        if not all_rules:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Alerts'),
                    'message': _('No reorder rules found that need replenishment.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }

        # Get all active users
        all_users = self.env['res.users'].search([('active', '=', True)])

        notified_users = 0
        admin_count = 0

        for user in all_users:
            is_admin = self._is_admin(user)

            if is_admin:
                # ADMIN: Get ALL reorder rules from ALL warehouses
                user_rules = all_rules
                admin_count += 1
            else:
                # REGULAR USER: Get only rules from assigned warehouses
                user_warehouses = self._get_user_warehouses(user)

                if not user_warehouses:
                    continue  # Skip users without warehouse assignment

                user_rules = all_rules.filtered(
                    lambda r: r.warehouse_id in user_warehouses
                )

            if not user_rules:
                continue

            # Build notification message
            product_lines = []
            for rule in user_rules:
                warehouse_name = rule.warehouse_id.name or 'Unknown'
                product_lines.append(
                    f"• [{warehouse_name}] {rule.product_id.display_name}: "
                    f"Need {rule.qty_to_order} {rule.product_uom.name}"
                )

            if is_admin:
                title = _("📢 Manual Alert - All Warehouses (Admin)")
                footer = _("\n\n✓ You are receiving all warehouse alerts as administrator.")
            else:
                warehouse_names = ', '.join(user_rules.mapped('warehouse_id.name'))
                title = _("📢 Manual Reorder Alert - Your Warehouses")
                footer = _("\n\n✓ Showing only: %s") % warehouse_names

            message = f"{title}\n\n" + "\n".join(product_lines) + footer

            self._send_notification(user, message)
            notified_users += 1

        # Show success message to whoever clicked the button
        if admin_count > 0:
            msg = _('Notifications sent to %s user(s) including %s administrator(s)') % (notified_users, admin_count)
        else:
            msg = _('Notifications sent to %s warehouse user(s)') % notified_users

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('✓ Success'),
                'message': msg,
                'type': 'success',
                'sticky': False,
            }
        }









# from odoo import models, api, _
# from odoo.exceptions import UserError
#
# class ReorderRuleNotification(models.Model):
#     _inherit = 'stock.warehouse.orderpoint'
#
#     # ------------------------------------------
#     # GET USER ALLOWED WAREHOUSES
#     # ------------------------------------------
#     def _get_user_warehouses(self, user):
#         if hasattr(user, 'stock_warehouse_ids') and user.stock_warehouse_ids:
#             return user.stock_warehouse_ids
#         return self.env['stock.warehouse'].search([])
#
#     # ------------------------------------------
#     # SEND NOTIFICATION TO USER
#     # ------------------------------------------
#     def _send_notification(self, user, message):
#         """Send notification using Odoo's bus notification system"""
#         # Use Odoo's notification bus - works in Odoo 19
#         self.env['bus.bus']._sendone(
#             user.partner_id,
#             'simple_notification',
#             {
#                 'type': 'info',
#                 'title': _('Reorder Alert'),
#                 'message': message,
#                 'sticky': False,
#             }
#         )
#
#     # ------------------------------------------
#     # AUTO - NOTIFICATION (CRON)
#     # ------------------------------------------
#     @api.model
#     def cron_send_reorder_notifications(self):
#         users = self.env['res.users'].search([('active', '=', True)])
#
#         for user in users:
#             warehouses = self._get_user_warehouses(user)
#
#             rules = self.search([
#                 ('warehouse_id', 'in', warehouses.ids),
#                 ('qty_to_order', '>', 0),
#                 ('product_id', '!=', False),
#             ])
#
#             if not rules:
#                 continue
#
#             product_lines = []
#             for r in rules:
#                 product_lines.append(
#                     f"• {r.product_id.display_name}: Need to order {r.qty_to_order} {r.product_uom.name}"
#                 )
#
#             message = _("📦 Reorder Alerts\n\n%s\n\nThese products need replenishment.") % "\n".join(product_lines)
#
#             self._send_notification(user, message)
#
#     # -----------------------------------------
#     # MANUAL BUTTON NOTIFICATION
#     # -----------------------------------------
#     def action_manual_reorder_notify(self):
#         rules = self.search([
#             ('qty_to_order', '>', 0),
#             ('product_id', '!=', False)
#         ])
#
#         if not rules:
#             return {
#                 'type': 'ir.actions.client',
#                 'tag': 'display_notification',
#                 'params': {
#                     'title': _('No Alerts'),
#                     'message': _('No reorder rules found that need replenishment.'),
#                     'type': 'warning',
#                     'sticky': False,
#                 }
#             }
#
#         users = self.env['res.users'].search([('active', '=', True)])
#         notified_count = 0
#
#         for user in users:
#             warehouses = self._get_user_warehouses(user)
#
#             user_rules = rules.filtered(lambda r: r.warehouse_id in warehouses)
#
#             if not user_rules:
#                 continue
#
#             product_lines = []
#             for r in user_rules:
#                 product_lines.append(
#                     f"• {r.product_id.display_name}: Need to order {r.qty_to_order} {r.product_uom.name}"
#                 )
#
#             message = _("📢 Manual Reorder Alerts\n\n%s\n\nPlease review these items.") % "\n".join(product_lines)
#
#             self._send_notification(user, message)
#             notified_count += 1
#
#         return {
#             'type': 'ir.actions.client',
#             'tag': 'display_notification',
#             'params': {
#                 'title': _('Success'),
#                 'message': _('Notifications sent to %s user(s)') % notified_count,
#                 'type': 'success',
#                 'sticky': False,
#             }
#         }
#
#
#

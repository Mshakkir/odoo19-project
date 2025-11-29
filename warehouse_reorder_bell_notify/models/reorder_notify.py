from odoo import models, api, _
from odoo.exceptions import UserError

class ReorderRuleNotification(models.Model):
    _inherit = 'stock.warehouse.orderpoint'

    # ------------------------------------------
    # GET USER ALLOWED WAREHOUSES
    # ------------------------------------------
    def _get_user_warehouses(self, user):
        if hasattr(user, 'stock_warehouse_ids') and user.stock_warehouse_ids:
            return user.stock_warehouse_ids
        return self.env['stock.warehouse'].search([])

    # ------------------------------------------
    # SEND NOTIFICATION TO USER
    # ------------------------------------------
    def _send_notification(self, user, message):
        """Send notification using Odoo's bus notification system"""
        # Use Odoo's notification bus - works in Odoo 19
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

    # ------------------------------------------
    # AUTO - NOTIFICATION (CRON)
    # ------------------------------------------
    @api.model
    def cron_send_reorder_notifications(self):
        users = self.env['res.users'].search([('active', '=', True)])

        for user in users:
            warehouses = self._get_user_warehouses(user)

            rules = self.search([
                ('warehouse_id', 'in', warehouses.ids),
                ('qty_to_order', '>', 0),
                ('product_id', '!=', False),
            ])

            if not rules:
                continue

            product_lines = []
            for r in rules:
                product_lines.append(
                    f"• {r.product_id.display_name}: Need to order {r.qty_to_order} {r.product_uom.name}"
                )

            message = _("📦 Reorder Alerts\n\n%s\n\nThese products need replenishment.") % "\n".join(product_lines)

            self._send_notification(user, message)

    # -----------------------------------------
    # MANUAL BUTTON NOTIFICATION
    # -----------------------------------------
    def action_manual_reorder_notify(self):
        rules = self.search([
            ('qty_to_order', '>', 0),
            ('product_id', '!=', False)
        ])

        if not rules:
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

        users = self.env['res.users'].search([('active', '=', True)])
        notified_count = 0

        for user in users:
            warehouses = self._get_user_warehouses(user)

            user_rules = rules.filtered(lambda r: r.warehouse_id in warehouses)

            if not user_rules:
                continue

            product_lines = []
            for r in user_rules:
                product_lines.append(
                    f"• {r.product_id.display_name}: Need to order {r.qty_to_order} {r.product_uom.name}"
                )

            message = _("📢 Manual Reorder Alerts\n\n%s\n\nPlease review these items.") % "\n".join(product_lines)

            self._send_notification(user, message)
            notified_count += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Notifications sent to %s user(s)') % notified_count,
                'type': 'success',
                'sticky': False,
            }
        }








# from odoo import models, fields, api, _
#
# class ReorderRuleNotification(models.Model):
#     _inherit = 'stock.warehouse.orderpoint'
#
#     def _get_user_warehouses(self, user):
#         """Returns warehouses allowed for the user"""
#         if hasattr(user, 'stock_warehouse_ids'):
#             return user.stock_warehouse_ids
#         return self.env['stock.warehouse'].search([])
#
#     # ---------------------------
#     # 1) AUTO NOTIFICATION (CRON)
#     # ---------------------------
#     @api.model
#     def cron_send_reorder_notifications(self):
#         users = self.env['res.users'].search([])
#
#         for user in users:
#             warehouses = self._get_user_warehouses(user)
#             if not warehouses:
#                 continue
#
#             rules = self.search([
#                 ('warehouse_id', 'in', warehouses.ids),
#                 ('qty_to_order', '>', 0),
#             ])
#
#             if not rules:
#                 continue
#
#             product_list = "\n".join([
#                 f"- {r.product_id.display_name}: Order {r.qty_to_order}"
#                 for r in rules
#             ])
#
#             message = _(
#                 "Reordering Alerts:\n%s\n"
#                 "These products in your warehouse require replenishment."
#             ) % product_list
#
#             user.partner_id.notify_info(message)
#
#     # -----------------------------------
#     # 2) MANUAL NOTIFICATION (BUTTON)
#     # -----------------------------------
#     def action_manual_reorder_notify(self):
#         rules = self.search([('qty_to_order', '>', 0)])
#         if not rules:
#             return
#
#         for user in self.env['res.users'].search([]):
#             warehouses = self._get_user_warehouses(user)
#             user_rules = rules.filtered(lambda r: r.warehouse_id in warehouses)
#
#             if not user_rules:
#                 continue
#
#             product_list = "\n".join([
#                 f"- {r.product_id.display_name}: Order {r.qty_to_order}"
#                 for r in user_rules
#             ])
#
#             message = _("Manual Reorder Alerts:\n%s") % product_list
#             user.partner_id.notify_info(message)

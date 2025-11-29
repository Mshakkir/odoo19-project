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
        """Send notification using Odoo's standard notification system"""
        try:
            # Create activity or send message via chatter
            self.env['mail.thread'].message_notify(
                partner_ids=[user.partner_id.id],
                body=message,
                subject=_('Reorder Rule Notification'),
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )
        except Exception:
            # Fallback: Create activity
            self.env['mail.activity'].create({
                'res_id': user.id,
                'res_model_id': self.env['ir.model']._get('res.users').id,
                'user_id': user.id,
                'summary': _('Reorder Alert'),
                'note': message,
                'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
            })

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

            product_list = "<br/>".join([
                f"<li><strong>{r.product_id.display_name}</strong>: Need to order <strong>{r.qty_to_order}</strong> {r.product_uom.name}</li>"
                for r in rules
            ])

            message = f"""
                <div style="padding: 10px; border-left: 4px solid #00A09D;">
                    <h3>📦 Reorder Alerts</h3>
                    <ul style="margin: 10px 0;">
                        {product_list}
                    </ul>
                    <p style="color: #666;">These products need replenishment.</p>
                </div>
            """

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
            raise UserError(_('No reorder rules found that need replenishment.'))

        users = self.env['res.users'].search([('active', '=', True)])
        notified_count = 0

        for user in users:
            warehouses = self._get_user_warehouses(user)

            user_rules = rules.filtered(lambda r: r.warehouse_id in warehouses)

            if not user_rules:
                continue

            product_list = "<br/>".join([
                f"<li><strong>{r.product_id.display_name}</strong>: Need to order <strong>{r.qty_to_order}</strong> {r.product_uom.name}</li>"
                for r in user_rules
            ])

            message = f"""
                <div style="padding: 10px; border-left: 4px solid #FF6B6B;">
                    <h3>📢 Manual Reorder Alerts</h3>
                    <ul style="margin: 10px 0;">
                        {product_list}
                    </ul>
                    <p style="color: #666;">Please review these items for replenishment.</p>
                </div>
            """

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

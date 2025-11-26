from odoo import models, fields, api


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    notification_channel_id = fields.Many2one(
        'discuss.channel',
        string='Notification Channel',
        help='Discuss channel for warehouse reorder notifications',
        copy=False
    )
    notification_user_ids = fields.Many2many(
        'res.users',
        'warehouse_notification_users_rel',
        'warehouse_id',
        'user_id',
        string='Notification Users',
        help='Users who will receive reorder notifications for this warehouse',
        domain=[('active', '=', True)]
    )

    def _get_or_create_notification_channel(self):
        """Get or create notification channel for this warehouse"""
        self.ensure_one()

        # Check if discuss.channel exists
        if 'discuss.channel' not in self.env:
            return False

        if not self.notification_channel_id or not self.notification_channel_id.exists():
            # Create new channel
            channel = self.env['discuss.channel'].sudo().create({
                'name': f'{self.name} - Reorder Notifications',
                'channel_type': 'channel',
                'description': f'Automatic reorder notifications for {self.name} warehouse',
                'group_public_id': False,  # Private channel
            })
            self.notification_channel_id = channel.id

        # Update channel members
        self._update_channel_members()

        return self.notification_channel_id

    def _update_channel_members(self):
        """Update channel members based on notification users"""
        self.ensure_one()

        if not self.notification_channel_id:
            return

        # Get users who should have access
        authorized_users = self.notification_user_ids

        # If no specific users, add all warehouse users
        if not authorized_users:
            authorized_users = self.env['res.users'].search([
                ('active', '=', True),
                '|',
                ('groups_id', 'in', self.env.ref('stock.group_stock_user').id),
                ('groups_id', 'in', self.env.ref('stock.group_stock_manager').id),
            ])

        # Get partner IDs
        partner_ids = authorized_users.mapped('partner_id').ids

        # Update channel members
        if partner_ids:
            self.notification_channel_id.sudo().write({
                'channel_partner_ids': [(6, 0, partner_ids)]
            })

    def action_open_notification_channel(self):
        """Open the notification channel in Discuss"""
        self.ensure_one()

        channel = self._get_or_create_notification_channel()

        if not channel:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Discuss Not Available',
                    'message': 'The Discuss app is not installed.',
                    'type': 'warning',
                    'sticky': False,
                }
            }

        return {
            'type': 'ir.actions.client',
            'tag': 'mail.action_discuss',
            'params': {
                'default_active_id': f'discuss.channel_{channel.id}',
            },
        }

    def action_update_channel_members(self):
        """Manually update channel members"""
        for warehouse in self:
            if warehouse.notification_channel_id:
                warehouse._update_channel_members()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': 'Channel members have been updated.',
                'type': 'success',
                'sticky': False,
            }
        }

    @api.model
    def create_all_warehouse_channels(self):
        """Create notification channels for all warehouses (can be called manually)"""
        warehouses = self.search([])
        for warehouse in warehouses:
            warehouse._get_or_create_notification_channel()
        return True

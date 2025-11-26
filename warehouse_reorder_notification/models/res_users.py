from odoo import models, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    def action_open_my_warehouse_channels(self):
        """Open Discuss showing user's warehouse notification channels"""
        self.ensure_one()

        # Check if discuss.channel exists
        if 'discuss.channel' not in self.env:
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

        # Find warehouses where user is a notification user
        warehouses = self.env['stock.warehouse'].search([
            ('notification_user_ids', 'in', [self.id])
        ])

        if not warehouses:
            # If no specific warehouses, find channels user is member of
            channels = self.env['discuss.channel'].search([
                ('name', 'ilike', 'Reorder Notifications'),
                ('channel_partner_ids', 'in', [self.partner_id.id])
            ])
        else:
            channels = warehouses.mapped('notification_channel_id')

        if channels:
            # Open first channel
            return {
                'type': 'ir.actions.client',
                'tag': 'mail.action_discuss',
                'params': {
                    'default_active_id': f'discuss.channel_{channels[0].id}',
                },
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'No Channels',
                    'message': 'You are not subscribed to any warehouse notification channels.',
                    'type': 'info',
                    'sticky': False,
                }
            }
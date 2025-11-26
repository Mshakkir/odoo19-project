from odoo import models, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    def action_open_reorder_notifications(self):
        """Open Discuss with ReorderBot conversation"""
        self.ensure_one()

        # Check if discuss.channel exists
        if 'discuss.channel' not in self.env:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Discuss Not Available',
                    'message': 'The Discuss app is not installed or available.',
                    'type': 'warning',
                    'sticky': False,
                }
            }

        # Get ReorderBot partner
        bot_partner = self.env.ref('warehouse_reorder_notification.partner_reorder_bot', raise_if_not_found=False)
        if not bot_partner:
            bot_partner = self.env['stock.warehouse.orderpoint']._get_reorder_bot_partner()

        # Find or create channel
        DiscussChannel = self.env['discuss.channel']
        channel = DiscussChannel.search([
            ('channel_type', '=', 'chat'),
            ('channel_partner_ids', 'in', [self.partner_id.id, bot_partner.id]),
        ], limit=1)

        if not channel:
            channel = DiscussChannel.sudo().create({
                'name': f'ReorderBot, {self.partner_id.name}',
                'channel_type': 'chat',
                'channel_partner_ids': [(6, 0, [self.partner_id.id, bot_partner.id])],
            })

        return {
            'type': 'ir.actions.client',
            'tag': 'mail.action_discuss',
            'params': {
                'default_active_id': f'discuss.channel_{channel.id}',
            },
        }
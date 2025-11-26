from odoo import models, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    def action_open_reorder_notifications(self):
        """Open Discuss with ReorderBot conversation"""
        self.ensure_one()

        # Get ReorderBot partner
        bot_partner = self.env.ref('warehouse_reorder_notification.partner_reorder_bot', raise_if_not_found=False)
        if not bot_partner:
            bot_partner = self.env['stock.warehouse.orderpoint']._get_reorder_bot_partner()

        # Find or create channel
        mail_channel = self.env['mail.channel']
        channel = mail_channel.search([
            ('channel_type', '=', 'chat'),
            ('channel_partner_ids', 'in', [self.partner_id.id, bot_partner.id]),
        ], limit=1)

        if not channel:
            channel = mail_channel.sudo().create({
                'name': f'ReorderBot, {self.partner_id.name}',
                'channel_type': 'chat',
                'channel_partner_ids': [(6, 0, [self.partner_id.id, bot_partner.id])],
            })

        return {
            'type': 'ir.actions.client',
            'tag': 'mail.action_discuss',
            'params': {
                'default_active_id': f'mail.channel_{channel.id}',
            },
        }

from odoo import models, fields, api


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    notification_user_ids = fields.Many2many(
        'res.users',
        'warehouse_notification_users_rel',
        'warehouse_id',
        'user_id',
        string='Notification Users',
        help='Users who will receive reorder notifications for this warehouse. Leave empty to notify all inventory users.',
        domain=[('active', '=', True)]
    )

    enable_reorder_notifications = fields.Boolean(
        string='Enable Reorder Notifications',
        default=True,
        help='Enable automatic reorder notifications for this warehouse'
    )

    def _get_notification_users(self):
        """Get users who should receive notifications for this warehouse"""
        self.ensure_one()

        if not self.enable_reorder_notifications:
            return self.env['res.users']

        # If specific users are defined, return them
        if self.notification_user_ids:
            return self.notification_user_ids

        # Otherwise, return all inventory users in the same company
        return self.env['res.users'].search([
            ('active', '=', True),
            '|',
            ('groups_id', 'in', self.env.ref('stock.group_stock_user').id),
            ('groups_id', 'in', self.env.ref('stock.group_stock_manager').id),
            '|',
            ('company_id', '=', self.company_id.id),
            ('company_id', '=', False),
        ])
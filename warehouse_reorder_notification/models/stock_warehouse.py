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
        stock_user_group = self.env.ref('stock.group_stock_user', raise_if_not_found=False)
        stock_manager_group = self.env.ref('stock.group_stock_manager', raise_if_not_found=False)

        if not stock_user_group and not stock_manager_group:
            return self.env['res.users']

        # Search for users with inventory access
        all_users = self.env['res.users'].search([('active', '=', True)])

        inventory_users = self.env['res.users']
        for user in all_users:
            # Check if user has stock groups
            user_groups = user.groups_id.ids
            has_stock_access = False

            if stock_user_group and stock_user_group.id in user_groups:
                has_stock_access = True
            if stock_manager_group and stock_manager_group.id in user_groups:
                has_stock_access = True

            # Check company match
            if has_stock_access:
                if not self.company_id or user.company_id == self.company_id or not user.company_id:
                    inventory_users |= user

        return inventory_users
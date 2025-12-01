from odoo import models, api, _


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, **kwargs):
        """Override search to filter activities based on warehouse assignment"""

        # Check if user is stock manager - they see everything
        if self.env.user.has_group('stock.group_stock_manager'):
            return super(MailActivity, self)._search(
                domain, offset=offset, limit=limit, order=order, **kwargs
            )

        # For stock users, filter orderpoint activities
        if self.env.user.has_group('stock.group_stock_user'):
            # Get warehouses where user is assigned OR no users assigned (empty means all users)
            assigned_warehouses = self.env['stock.warehouse'].sudo().search([
                '|',
                ('notification_user_ids', '=', False),  # No specific users = all users can see
                ('notification_user_ids', 'in', [self.env.user.id])  # User is specifically assigned
            ])

            # Get orderpoints for these warehouses
            user_orderpoints = self.env['stock.warehouse.orderpoint'].sudo().search([
                ('warehouse_id', 'in', assigned_warehouses.ids)
            ])

            orderpoint_ids = user_orderpoints.ids

            # Add domain to filter activities
            # Show: 1) All non-orderpoint activities OR 2) Only assigned warehouse orderpoint activities
            warehouse_domain = [
                '|',
                ('res_model', '!=', 'stock.warehouse.orderpoint'),
                '&',
                ('res_model', '=', 'stock.warehouse.orderpoint'),
                ('res_id', 'in', orderpoint_ids)
            ]

            # Combine with original domain
            if domain:
                domain = ['&'] + warehouse_domain + domain
            else:
                domain = warehouse_domain

        return super(MailActivity, self)._search(
            domain, offset=offset, limit=limit, order=order, **kwargs
        )

    def read(self, fields=None, load='_classic_read'):
        """Override read to filter out activities user shouldn't see"""
        # First check if user should see these activities
        if not self.env.user.has_group('stock.group_stock_manager'):
            if self.env.user.has_group('stock.group_stock_user'):
                # Filter activities
                allowed_activities = self.env['mail.activity']

                for activity in self:
                    if activity.res_model == 'stock.warehouse.orderpoint':
                        # Check if user has access to this orderpoint's warehouse
                        orderpoint = self.env['stock.warehouse.orderpoint'].sudo().browse(activity.res_id)
                        if orderpoint.exists():
                            warehouse = orderpoint.warehouse_id
                            # Allow if: no specific users assigned OR user is in the list
                            if not warehouse.notification_user_ids or self.env.user in warehouse.notification_user_ids:
                                allowed_activities |= activity
                    else:
                        # Non-orderpoint activities - allow all
                        allowed_activities |= activity

                # Replace self with filtered recordset
                self = allowed_activities

        return super(MailActivity, self).read(fields=fields, load=load)











# from odoo import models, api
#
#
# class MailActivity(models.Model):
#     _inherit = 'mail.activity'
#
#     @api.model
#     def _search(self, domain, offset=0, limit=None, order=None, **kwargs):
#         """Override search to filter activities based on warehouse assignment"""
#
#         # Check if user is stock manager - they see everything
#         if self.env.user.has_group('stock.group_stock_manager'):
#             return super(MailActivity, self)._search(
#                 domain, offset=offset, limit=limit, order=order, **kwargs
#             )
#
#         # For stock users, filter orderpoint activities
#         if self.env.user.has_group('stock.group_stock_user'):
#             # Get orderpoints for user's assigned warehouses
#             user_orderpoints = self.env['stock.warehouse.orderpoint'].sudo().search([
#                 '|',
#                 ('warehouse_id.notification_user_ids', '=', False),
#                 ('warehouse_id.notification_user_ids', 'in', [self.env.user.id])
#             ])
#
#             orderpoint_ids = user_orderpoints.ids
#
#             # Add domain to filter activities
#             # Show: 1) All non-orderpoint activities OR 2) Only assigned orderpoint activities
#             warehouse_domain = [
#                 '|',
#                 ('res_model', '!=', 'stock.warehouse.orderpoint'),
#                 '&',
#                 ('res_model', '=', 'stock.warehouse.orderpoint'),
#                 ('res_id', 'in', orderpoint_ids)
#             ]
#
#             # Combine with original domain
#             domain = domain + warehouse_domain if domain else warehouse_domain
#
#         return super(MailActivity, self)._search(
#             domain, offset=offset, limit=limit, order=order, **kwargs
#         )
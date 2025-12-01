from odoo import models, api, fields, _


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    # Add computed field to store warehouse info for filtering
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Related Warehouse',
        compute='_compute_warehouse_id',
        store=True,
        compute_sudo=True
    )

    @api.depends('res_model', 'res_id')
    def _compute_warehouse_id(self):
        """Compute warehouse for orderpoint activities"""
        for activity in self:
            if activity.res_model == 'stock.warehouse.orderpoint' and activity.res_id:
                orderpoint = self.env['stock.warehouse.orderpoint'].sudo().browse(activity.res_id)
                activity.warehouse_id = orderpoint.warehouse_id.id if orderpoint.exists() else False
            else:
                activity.warehouse_id = False

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, **kwargs):
        """Override search to filter activities based on warehouse assignment"""

        # Stock Managers see everything - no filtering
        if self.env.user.has_group('stock.group_stock_manager'):
            return super()._search(domain, offset=offset, limit=limit, order=order, **kwargs)

        # For regular Stock Users - filter by warehouse assignment
        if self.env.user.has_group('stock.group_stock_user'):
            # Get warehouses assigned to current user
            assigned_warehouses = self.env['stock.warehouse'].sudo().search([
                ('notification_user_ids', 'in', [self.env.user.id])
            ])

            # Get warehouses with NO users assigned (empty = visible to all stock users)
            unassigned_warehouses = self.env['stock.warehouse'].sudo().search([
                ('notification_user_ids', '=', False),
                ('enable_reorder_notifications', '=', True)
            ])

            # Combine both sets of warehouses
            allowed_warehouses = assigned_warehouses | unassigned_warehouses

            if allowed_warehouses:
                # Filter: Show non-orderpoint activities OR orderpoint activities from allowed warehouses
                warehouse_filter = [
                    '|',
                    ('res_model', '!=', 'stock.warehouse.orderpoint'),
                    ('warehouse_id', 'in', allowed_warehouses.ids)
                ]
            else:
                # If no warehouses assigned and no unassigned warehouses, hide all orderpoint activities
                warehouse_filter = [('res_model', '!=', 'stock.warehouse.orderpoint')]

            # Combine with original domain
            if domain:
                domain = ['&'] + warehouse_filter + domain
            else:
                domain = warehouse_filter

        return super()._search(domain, offset=offset, limit=limit, order=order, **kwargs)









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
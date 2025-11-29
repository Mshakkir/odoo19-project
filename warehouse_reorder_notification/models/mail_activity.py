from odoo import models, api


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
            # Get orderpoints for user's assigned warehouses
            user_orderpoints = self.env['stock.warehouse.orderpoint'].sudo().search([
                '|',
                ('warehouse_id.notification_user_ids', '=', False),
                ('warehouse_id.notification_user_ids', 'in', [self.env.user.id])
            ])

            orderpoint_ids = user_orderpoints.ids

            # Add domain to filter activities
            # Show: 1) All non-orderpoint activities OR 2) Only assigned orderpoint activities
            warehouse_domain = [
                '|',
                ('res_model', '!=', 'stock.warehouse.orderpoint'),
                '&',
                ('res_model', '=', 'stock.warehouse.orderpoint'),
                ('res_id', 'in', orderpoint_ids)
            ]

            # Combine with original domain
            domain = domain + warehouse_domain if domain else warehouse_domain

        return super(MailActivity, self)._search(
            domain, offset=offset, limit=limit, order=order, **kwargs
        )
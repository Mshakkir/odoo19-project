# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    allowed_warehouse_ids = fields.Many2many(
        'stock.warehouse',
        'res_users_warehouse_rel',
        'user_id',
        'warehouse_id',
        string='Allowed Warehouses',
        help='Warehouses that this user can access in the inventory dashboard. '
             'If empty, user can see all warehouses.'
    )

    @api.model
    def get_user_warehouse_domain(self):
        """
        Returns domain to filter operations by user's allowed warehouses.
        If user has no specific warehouses assigned, returns empty domain (shows all).
        """
        user = self.env.user
        if user.allowed_warehouse_ids:
            return [('picking_type_id.warehouse_id', 'in', user.allowed_warehouse_ids.ids)]
        return []

    def write(self, vals):
        """Clear cache when warehouse assignments change"""
        res = super(ResUsers, self).write(vals)
        if 'allowed_warehouse_ids' in vals:
            self.env['stock.picking'].clear_caches()
        return res
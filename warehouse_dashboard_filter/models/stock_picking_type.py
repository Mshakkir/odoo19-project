# -*- coding: utf-8 -*-

from odoo import models, api


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    @api.model
    def get_stock_picking_action_picking_type(self):
        """
        Override the method that generates dashboard actions to include warehouse filter
        This is called when clicking on dashboard cards
        """
        action = super(StockPickingType, self).get_stock_picking_action_picking_type()

        # Add warehouse filter to the action context
        if action and isinstance(action, dict):
            context = action.get('context', {})
            if isinstance(context, str):
                context = eval(context)
            context['filter_by_user_warehouse'] = True
            action['context'] = context

            # Also add to domain if user has warehouse restrictions
            warehouse_domain = self.env.user.get_user_warehouse_domain()
            if warehouse_domain:
                existing_domain = action.get('domain', [])
                if existing_domain:
                    action['domain'] = ['&'] + existing_domain + warehouse_domain
                else:
                    action['domain'] = warehouse_domain

        return action

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        """
        Filter picking types shown in dashboard by user's allowed warehouses
        """
        # Check if we should filter by warehouse
        user = self.env.user
        if user.allowed_warehouse_ids:
            warehouse_domain = [('warehouse_id', 'in', user.allowed_warehouse_ids.ids)]
            domain = domain or []
            if domain:
                domain = ['&'] + domain + warehouse_domain
            else:
                domain = warehouse_domain

        return super(StockPickingType, self).search_read(
            domain=domain,
            fields=fields,
            offset=offset,
            limit=limit,
            order=order
        )

    @api.model
    def search(self, domain, offset=0, limit=None, order=None, count=False):
        """
        Filter picking types by user's allowed warehouses
        """
        user = self.env.user
        if user.allowed_warehouse_ids:
            warehouse_domain = [('warehouse_id', 'in', user.allowed_warehouse_ids.ids)]
            domain = domain or []
            if domain:
                domain = ['&'] + domain + warehouse_domain
            else:
                domain = warehouse_domain

        return super(StockPickingType, self).search(
            domain=domain,
            offset=offset,
            limit=limit,
            order=order,
            count=count
        )
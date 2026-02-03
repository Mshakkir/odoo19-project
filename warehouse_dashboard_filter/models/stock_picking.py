# -*- coding: utf-8 -*-

from odoo import models, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        """
        Override search_read to filter pickings by user's allowed warehouses
        when called from dashboard/overview context
        """
        # Check if this is a dashboard call (you can customize this condition)
        if self.env.context.get('filter_by_user_warehouse', False):
            warehouse_domain = self.env.user.get_user_warehouse_domain()
            if warehouse_domain:
                domain = domain or []
                domain = ['&'] + domain + warehouse_domain if domain else warehouse_domain

        return super(StockPicking, self).search_read(
            domain=domain,
            fields=fields,
            offset=offset,
            limit=limit,
            order=order
        )

    @api.model
    def search(self, domain, offset=0, limit=None, order=None, count=False):
        """
        Override search to filter pickings by user's allowed warehouses
        when appropriate
        """
        # Apply warehouse filter if context flag is set
        if self.env.context.get('filter_by_user_warehouse', False):
            warehouse_domain = self.env.user.get_user_warehouse_domain()
            if warehouse_domain:
                domain = domain or []
                if domain:
                    domain = ['&'] + domain + warehouse_domain
                else:
                    domain = warehouse_domain

        return super(StockPicking, self).search(
            domain,
            offset=offset,
            limit=limit,
            order=order,
            count=count
        )

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        """
        Override read_group for dashboard statistics
        """
        if self.env.context.get('filter_by_user_warehouse', False):
            warehouse_domain = self.env.user.get_user_warehouse_domain()
            if warehouse_domain:
                domain = domain or []
                if domain:
                    domain = ['&'] + domain + warehouse_domain
                else:
                    domain = warehouse_domain

        return super(StockPicking, self).read_group(
            domain=domain,
            fields=fields,
            groupby=groupby,
            offset=offset,
            limit=limit,
            orderby=orderby,
            lazy=lazy
        )
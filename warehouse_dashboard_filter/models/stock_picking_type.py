# -*- coding: utf-8 -*-
from odoo import models, api


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        """
        Override search_read to filter operation types by warehouse in the dashboard.

        This ensures that:
        1. Dashboard shows ONLY user's warehouse operation types
        2. But direct record access (via browse/read) still works for inter-warehouse transfers

        The key insight: Dashboard uses search_read(), but validation uses browse()/read()
        """
        # Get current user's warehouse groups
        user = self.env.user

        # Check which warehouse group the user belongs to
        fyh_group = self.env.ref('warehouse_transfer_automation.group_fyh_warehouse', raise_if_not_found=False)
        dmm_group = self.env.ref('warehouse_transfer_automation.group_dmm_warehouse', raise_if_not_found=False)
        bld_group = self.env.ref('warehouse_transfer_automation.group_bld_warehouse', raise_if_not_found=False)

        # Skip filtering for admin users
        if user.has_group('base.group_system'):
            return super(StockPickingType, self).search_read(domain, fields, offset, limit, order)

        # Apply warehouse-specific filter
        warehouse_domain = None

        if fyh_group and user.has_group('warehouse_transfer_automation.group_fyh_warehouse'):
            # FYH user: show only JED-Fyh operation types
            warehouse_domain = [('warehouse_id.name', '=', 'JED-Fyh')]

        elif dmm_group and user.has_group('warehouse_transfer_automation.group_dmm_warehouse'):
            # DMM user: show only DMM-Wh1 operation types
            warehouse_domain = [('warehouse_id.name', '=', 'DMM-Wh1')]

        elif bld_group and user.has_group('warehouse_transfer_automation.group_bld_warehouse'):
            # BLD user: show only JED-Bld operation types
            warehouse_domain = [('warehouse_id.name', '=', 'JED-Bld')]

        # Combine with existing domain
        if warehouse_domain:
            if domain:
                domain = ['&'] + domain + warehouse_domain
            else:
                domain = warehouse_domain

        return super(StockPickingType, self).search_read(domain, fields, offset, limit, order)

    @api.model
    def search(self, args, offset=0, limit=None, order=None, **kwargs):
        """
        Override search to filter operation types by warehouse in list views.

        This ensures list views and kanban views also show only user's warehouse.
        """
        # Get current user's warehouse groups
        user = self.env.user

        # Check which warehouse group the user belongs to
        fyh_group = self.env.ref('warehouse_transfer_automation.group_fyh_warehouse', raise_if_not_found=False)
        dmm_group = self.env.ref('warehouse_transfer_automation.group_dmm_warehouse', raise_if_not_found=False)
        bld_group = self.env.ref('warehouse_transfer_automation.group_bld_warehouse', raise_if_not_found=False)

        # Skip filtering for admin users
        if user.has_group('base.group_system'):
            return super(StockPickingType, self).search(args, offset=offset, limit=limit, order=order, **kwargs)

        # Apply warehouse-specific filter
        warehouse_domain = None

        if fyh_group and user.has_group('warehouse_transfer_automation.group_fyh_warehouse'):
            warehouse_domain = [('warehouse_id.name', '=', 'JED-Fyh')]

        elif dmm_group and user.has_group('warehouse_transfer_automation.group_dmm_warehouse'):
            warehouse_domain = [('warehouse_id.name', '=', 'DMM-Wh1')]

        elif bld_group and user.has_group('warehouse_transfer_automation.group_bld_warehouse'):
            warehouse_domain = [('warehouse_id.name', '=', 'JED-Bld')]

        # Combine with existing domain
        if warehouse_domain:
            if args:
                args = ['&'] + args + warehouse_domain
            else:
                args = warehouse_domain

        return super(StockPickingType, self).search(args, offset=offset, limit=limit, order=order, **kwargs)
# -*- coding: utf-8 -*-
from odoo import models
import json


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def get_views(self, views, options=None):
        """Override to inject custom js_class into tree view"""
        result = super().get_views(views, options=options)

        # Add js_class to tree view
        for view_type in result.get('views', {}):
            if view_type == 'tree':
                arch = result['views'][view_type].get('arch', '')
                if isinstance(arch, str) and '<tree' in arch and 'js_class=' not in arch:
                    # Inject js_class attribute
                    arch = arch.replace('<tree', '<tree js_class="sale_order_tree_date_filter"', 1)
                    result['views'][view_type]['arch'] = arch

        return result
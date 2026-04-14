# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    # In Odoo 19, the default warehouse field on res.users may be named
    # differently depending on installed modules. We resolve it safely at
    # runtime instead of using @depends (which fails if the field is absent).

    warehouse_analytic_account_id = fields.Many2one(
        comodel_name='account.analytic.account',
        string='Warehouse Analytic Account',
        compute='_compute_warehouse_analytic_account_id',
        store=False,
    )

    def _compute_warehouse_analytic_account_id(self):
        # Try both known field names for the default warehouse across Odoo versions
        warehouse_field = None
        for fname in ('property_warehouse_id', 'default_warehouse_id', 'warehouse_id'):
            if fname in self._fields:
                warehouse_field = fname
                break

        for user in self:
            analytic = False
            if warehouse_field:
                wh = getattr(user, warehouse_field, False)
                if wh and hasattr(wh, 'analytic_account_id'):
                    analytic = wh.analytic_account_id
            user.warehouse_analytic_account_id = analytic

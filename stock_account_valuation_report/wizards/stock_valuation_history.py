# # Copyright 2019 Eficent Business and IT Consulting Services, S.L.
# # Copyright 2019 Aleph Objects, Inc.
# # License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
#
# import ast
#
# from odoo import fields, models
# from odoo.osv import expression
#
#
# class StockValuationHistory(models.TransientModel):
#     _name = "stock.valuation.history"
#     _description = "Stock Valuation History"
#     _rec_name = "inventory_datetime"
#
#     inventory_datetime = fields.Datetime(
#         "Dual Valuation at Date",
#         help="Choose a date to get the valuation at that date",
#         default=fields.Datetime.now,
#     )
#
#     def open_at_date(self):
#         action = self.env["ir.actions.act_window"]._for_xml_id(
#             "stock_account_valuation_report.product_valuation_action"
#         )
#         domain = [("type", "=", "consu")]
#         product_id = self.env.context.get("product_id", False)
#         product_tmpl_id = self.env.context.get("product_tmpl_id", False)
#         if product_id:
#             domain = expression.AND([domain, [("id", "=", product_id)]])
#         elif product_tmpl_id:
#             domain = expression.AND(
#                 [domain, [("product_tmpl_id", "=", product_tmpl_id)]]
#             )
#         action["domain"] = domain
#         if self.inventory_datetime:
#             # Use ast.literal_eval instead of deprecated safe_eval for simple dicts
#             action_context = ast.literal_eval(action["context"])
#             action_context["at_date"] = self.inventory_datetime
#             action["context"] = str(action_context)
#         return action
# Copyright 2019 Eficent Business and IT Consulting Services, S.L.
# Copyright 2019 Aleph Objects, Inc.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
# Copyright 2019 Eficent Business and IT Consulting Services, S.L.
# Copyright 2019 Aleph Objects, Inc.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

# Copyright 2019 Eficent Business and IT Consulting Services, S.L.
# Copyright 2019 Aleph Objects, Inc.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import ast

from odoo import fields, models
from odoo.osv import expression


class StockValuationHistory(models.TransientModel):
    _name = "stock.valuation.history"
    _description = "Stock Valuation History"
    _rec_name = "inventory_datetime"

    inventory_datetime = fields.Datetime(
        "Dual Valuation at Date",
        help="Choose a date to get the valuation at that date",
        default=fields.Datetime.now,
    )

    def open_at_date(self):
        """Open the SVL list filtered up to inventory_datetime."""
        # Reference our own action – no dependency on external XML IDs
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "stock_account_valuation_report.svl_action"
        )

        ctx = {}
        if action.get("context"):
            try:
                ctx = ast.literal_eval(action["context"])
            except Exception:
                ctx = {}

        if self.inventory_datetime:
            ctx["at_date"] = self.inventory_datetime

        action["context"] = str(ctx)

        # Build domain
        domain = []
        product_id = self.env.context.get("product_id", False)
        product_tmpl_id = self.env.context.get("product_tmpl_id", False)
        if product_id:
            domain = expression.AND([domain, [("product_id", "=", product_id)]])
        elif product_tmpl_id:
            domain = expression.AND(
                [domain, [("product_id.product_tmpl_id", "=", product_tmpl_id)]]
            )

        if self.inventory_datetime:
            domain = expression.AND(
                [domain, [("create_date", "<=", self.inventory_datetime)]]
            )

        if domain:
            action["domain"] = domain

        return action
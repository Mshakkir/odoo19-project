# Copyright 2019 Tecnativa - David Vidal
# Copyright 2025 - Odoo 19 CE Conversion
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tools.sql import column_exists


def _pre_init_global_discount_fields(env):
    """Pre-initialize global discount fields to avoid recomputation on install"""
    if not column_exists(env.cr, "account_move", "amount_global_discount"):
        env.cr.execute(
            """
            ALTER TABLE account_move
            ADD COLUMN amount_global_discount numeric DEFAULT 0
            """
        )
        env.cr.execute(
            """
            ALTER TABLE account_move 
            ALTER COLUMN amount_global_discount DROP DEFAULT
            """
        )

    if not column_exists(
            env.cr, "account_move", "amount_untaxed_before_global_discounts"
    ):
        env.cr.execute(
            """
            ALTER TABLE account_move
            ADD COLUMN amount_untaxed_before_global_discounts numeric
            """
        )
        env.cr.execute(
            """
            UPDATE account_move 
            SET amount_untaxed_before_global_discounts = amount_untaxed
            """
        )
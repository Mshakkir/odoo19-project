from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    customer_credit_limit = fields.Float(string="Customer Credit Limit")

    fiscalyear_last_day = fields.Integer(
        related='company_id.fiscalyear_last_day', readonly=False
    )
    fiscalyear_last_month = fields.Selection(
        related='company_id.fiscalyear_last_month', readonly=False
    )
    tax_lock_date = fields.Date(
        related='company_id.hard_lock_date', readonly=False
    )
    sale_lock_date = fields.Date(
        related='company_id.hard_lock_date', readonly=False
    )
    purchase_lock_date = fields.Date(
        related='company_id.hard_lock_date', readonly=False
    )
    hard_lock_date = fields.Date(
        related='company_id.hard_lock_date', readonly=False
    )
    fiscalyear_lock_date = fields.Date(
        related='company_id.fiscalyear_lock_date', readonly=False
    )
    group_fiscal_year = fields.Boolean(
        string='Fiscal Years', implied_group='om_fiscal_year.group_fiscal_year'
    )

# from odoo import api, fields, models
#
#
# class ResConfigSettings(models.TransientModel):
#     _inherit = 'res.config.settings'
#
#     # 👇 Add the missing field
#     customer_credit_limit = fields.Float(
#         string="Customer Credit Limit",
#         help="Default credit limit for customers. This can be used to restrict sales or invoices beyond the limit."
#     )
#
#     fiscalyear_last_day = fields.Integer(
#         related='company_id.fiscalyear_last_day', readonly=False
#     )
#     fiscalyear_last_month = fields.Selection(
#         related='company_id.fiscalyear_last_month', readonly=False
#     )
#     tax_lock_date = fields.Date(
#         related='company_id.hard_lock_date', readonly=False
#     )
#     sale_lock_date = fields.Date(
#         related='company_id.hard_lock_date', readonly=False
#     )
#     purchase_lock_date = fields.Date(
#         related='company_id.hard_lock_date', readonly=False
#     )
#     hard_lock_date = fields.Date(
#         related='company_id.hard_lock_date', readonly=False
#     )
#     fiscalyear_lock_date = fields.Date(
#         related='company_id.fiscalyear_lock_date', readonly=False
#     )
#     group_fiscal_year = fields.Boolean(
#         string='Fiscal Years',
#         implied_group='om_fiscal_year.group_fiscal_year'
#     )

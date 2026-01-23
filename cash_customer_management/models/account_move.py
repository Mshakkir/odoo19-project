from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    is_cash_customer = fields.Boolean(
        string='Cash Customer Invoice',
        compute='_compute_is_cash_customer',
        store=True,
        help='Automatically set when Cash Customer is selected'
    )

    actual_customer_name = fields.Char(
        string='Customer Name',
        help='Actual customer name for invoice printing'
    )

    actual_customer_mobile = fields.Char(
        string='Mobile Number',
        help='Customer mobile number'
    )

    actual_customer_address = fields.Text(
        string='Customer Address',
        help='Customer address for invoice'
    )

    actual_customer_email = fields.Char(
        string='Email',
        help='Customer email'
    )

    @api.depends('partner_id')
    def _compute_is_cash_customer(self):
        """Check if selected customer is the Cash Customer"""
        cash_customer = self.env.ref('cash_customer_management.cash_customer_partner', raise_if_not_found=False)
        for record in self:
            record.is_cash_customer = (cash_customer and record.partner_id == cash_customer)

    @api.onchange('partner_id')
    def _onchange_partner_id_clear_fields(self):
        """Clear custom fields when changing customer"""
        if not self.is_cash_customer:
            self.actual_customer_name = False
            self.actual_customer_mobile = False
            self.actual_customer_address = False
            self.actual_customer_email = False
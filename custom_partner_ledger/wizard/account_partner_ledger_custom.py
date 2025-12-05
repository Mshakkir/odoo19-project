# -*- coding: utf-8 -*-
from odoo import fields, models, api, _


class AccountPartnerLedgerCustom(models.TransientModel):
    _inherit = "account.report.partner.ledger"

    show_details = fields.Boolean(
        string='Show Details',
        default=False,
        help="Show detailed transaction information in the report"
    )

    def _get_report_data(self, data):
        """Override to add show_details to report data"""
        data = super(AccountPartnerLedgerCustom, self)._get_report_data(data)
        data['form'].update({
            'show_details': self.show_details,
        })
        return data

    def button_show_details(self):
        """Action for Show Details button"""
        self.show_details = not self.show_details
        return {
            'type': 'ir.actions.do_nothing',
        }
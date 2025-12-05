# -*- coding: utf-8 -*-
from odoo import fields, models, api, _


class AccountPartnerLedgerCustom(models.TransientModel):
    _inherit = "account.report.partner.ledger"

    show_details = fields.Boolean(
        string='Show Transaction Details',
        default=True,  # Set to True by default to show transaction lines
        help="Show detailed transaction lines in the report. "
             "Uncheck to show only partner summaries."
    )

    def _get_report_data(self, data):
        """Override to add show_details to report data"""
        data = super(AccountPartnerLedgerCustom, self)._get_report_data(data)
        data['form'].update({
            'show_details': self.show_details,
        })
        return data
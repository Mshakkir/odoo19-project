# -*- coding: utf-8 -*-
from odoo import fields, models, api, _


class AccountPartnerLedgerCustom(models.TransientModel):
    _inherit = "account.report.partner.ledger"
    _description = "Custom Account Partner Ledger"

    def action_show_details(self):
        """
        Show partner ledger details in a dedicated tree view
        """
        self.ensure_one()

        # Prepare wizard data
        wizard_data = {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'journal_ids': self.journal_ids.ids if self.journal_ids else [],
            'target_move': self.target_move,
            'result_selection': self.result_selection,
            'partner_ids': self.partner_ids.ids if self.partner_ids else [],
            'amount_currency': self.amount_currency,
            'reconciled': self.reconciled,
        }

        # Generate detail records
        detail_model = self.env['partner.ledger.detail']
        detail_model.get_partner_ledger_details(wizard_data)

        # Return action to open detail view
        return {
            'name': _('Partner Ledger Details'),
            'type': 'ir.actions.act_window',
            'res_model': 'partner.ledger.detail',
            'view_mode': 'tree',
            'view_id': self.env.ref('custom_partner_ledger.view_partner_ledger_detail_tree').id,
            'search_view_id': self.env.ref('custom_partner_ledger.view_partner_ledger_detail_search').id,
            'context': {
                'search_default_group_by_partner': 1,
                'search_default_filter_transactions': 1,
            },
            'target': 'current',
        }
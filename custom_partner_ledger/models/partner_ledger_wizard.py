# -*- coding: utf-8 -*-
# File: custom_partner_ledger/models/partner_ledger_wizard.py
from odoo import fields, models, api, _
import logging

_logger = logging.getLogger(__name__)


class AccountPartnerLedgerCustom(models.TransientModel):
    _inherit = "account.report.partner.ledger"
    _description = "Custom Account Partner Ledger"

    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        string='Analytic Accounts (Warehouses)',
        help='Filter by specific analytic accounts/warehouses'
    )

    def action_show_details(self):
        """
        Show partner ledger details in a dedicated list view
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
            'analytic_account_ids': self.analytic_account_ids.ids if self.analytic_account_ids else [],
        }

        # Generate detail records
        detail_model = self.env['partner.ledger.detail']
        detail_model.get_partner_ledger_details(wizard_data)

        # Return action to open detail view
        return {
            'name': _('Partner Ledger Details'),
            'type': 'ir.actions.act_window',
            'res_model': 'partner.ledger.detail',
            'view_mode': 'list',
            'views': [(self.env.ref('custom_partner_ledger.view_partner_ledger_detail_tree').id, 'list')],
            'search_view_id': [self.env.ref('custom_partner_ledger.view_partner_ledger_detail_search').id],
            'context': {
                'search_default_group_by_partner': 1,
            },
            'target': 'current',
        }

    def _get_report_data(self, data):
        """
        Override to add analytic account data - MUST call super() first
        """
        _logger.info(f"=== WIZARD DEBUG START === self.reconciled = {self.reconciled}")

        # IMPORTANT: Call parent method first - this sets reconciled and amount_currency
        data = super()._get_report_data(data)

        _logger.info(f"=== WIZARD DEBUG AFTER SUPER === data['form']['reconciled'] = {data['form'].get('reconciled')}")

        # Now add our custom analytic account data
        data['form'].update({
            'analytic_account_ids': self.analytic_account_ids.ids,
        })

        _logger.info(
            f"=== WIZARD DEBUG FINAL === reconciled={data['form']['reconciled']}, analytic_ids={data['form']['analytic_account_ids']}")

        return data
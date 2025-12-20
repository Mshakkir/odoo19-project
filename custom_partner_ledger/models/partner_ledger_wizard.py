# -*- coding: utf-8 -*-
from odoo import fields, models, api, _


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

    def _print_report(self, data):
        """
        Override to pass analytic account data to the report
        """
        # Call parent method to get properly formatted data
        data = super()._print_report(data)

        # This won't work because parent returns an action, not data
        # So we need to use a different approach
        return data

    def _get_report_data(self, data):
        """
        Override to add analytic account data
        """
        # Call parent method first
        data = super()._get_report_data(data)

        # Add analytic account data
        data['form'].update({
            'analytic_account_ids': self.analytic_account_ids.ids,
        })

        return data
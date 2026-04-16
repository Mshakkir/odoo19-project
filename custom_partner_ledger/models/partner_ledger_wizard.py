

# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
from odoo import fields, models, api, _


class AccountPartnerLedgerCustom(models.TransientModel):
    _inherit = "account.report.partner.ledger"
    _description = "Custom Account Partner Ledger"

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
#
# # -*- coding: utf-8 -*-
# from odoo import fields, models, api, _
#
#
# class AccountPartnerLedgerCustom(models.TransientModel):
#     _inherit = "account.report.partner.ledger"
#     _description = "Custom Account Partner Ledger"
#
#     # ── Manual exchange-rate fields ──────────────────────────────────────────
#     use_manual_rate = fields.Boolean(
#         string='Use Manual Exchange Rate',
#         default=False,
#     )
#     manual_rate_currency_id = fields.Many2one(
#         'res.currency',
#         string='Foreign Currency',
#         help='The foreign currency whose rate you want to specify manually.',
#     )
#     manual_currency_exchange_rate = fields.Float(
#         string='Exchange Rate',
#         digits=(12, 6),
#         default=1.0,
#         help='How many SAR (company currency) equal 1 unit of the foreign currency.\n'
#              'e.g. 1 INR = 24.000000 SAR',
#     )
#     company_currency_id = fields.Many2one(
#         'res.currency',
#         string='Company Currency',
#         default=lambda self: self.env.company.currency_id,
#         readonly=True,
#     )
#     # ── Rate display string shown below the rate field ───────────────────────
#     rate_display = fields.Char(
#         string='Rate Preview',
#         compute='_compute_rate_display',
#     )
#
#     @api.depends('manual_rate_currency_id', 'manual_currency_exchange_rate', 'company_currency_id')
#     def _compute_rate_display(self):
#         for rec in self:
#             if rec.manual_rate_currency_id and rec.company_currency_id:
#                 rec.rate_display = (
#                     f"1 {rec.manual_rate_currency_id.name} = "
#                     f"{rec.manual_currency_exchange_rate:.6f} "
#                     f"{rec.company_currency_id.name}"
#                 )
#             else:
#                 rec.rate_display = ''
#
#     # ── Actions ──────────────────────────────────────────────────────────────
#     def _build_wizard_data(self):
#         """Collect all wizard fields into a dict for downstream use."""
#         return {
#             'date_from': self.date_from,
#             'date_to': self.date_to,
#             'journal_ids': self.journal_ids.ids if self.journal_ids else [],
#             'target_move': self.target_move,
#             'result_selection': self.result_selection,
#             'partner_ids': self.partner_ids.ids if self.partner_ids else [],
#             'amount_currency': self.amount_currency,
#             'reconciled': self.reconciled,
#             # ── manual rate ──
#             'use_manual_rate': self.use_manual_rate,
#             'manual_rate_currency_id': self.manual_rate_currency_id.id if self.manual_rate_currency_id else False,
#             'manual_currency_exchange_rate': self.manual_currency_exchange_rate if self.use_manual_rate else 1.0,
#         }
#
#     def action_show_details(self):
#         """Show partner ledger details in a dedicated list view."""
#         self.ensure_one()
#         wizard_data = self._build_wizard_data()
#
#         detail_model = self.env['partner.ledger.detail']
#         detail_model.get_partner_ledger_details(wizard_data)
#
#         return {
#             'name': _('Partner Ledger Details'),
#             'type': 'ir.actions.act_window',
#             'res_model': 'partner.ledger.detail',
#             'view_mode': 'list',
#             'views': [(self.env.ref('custom_partner_ledger.view_partner_ledger_detail_tree').id, 'list')],
#             'search_view_id': [self.env.ref('custom_partner_ledger.view_partner_ledger_detail_search').id],
#             'context': {
#                 'search_default_group_by_partner': 1,
#             },
#             'target': 'current',
#         }
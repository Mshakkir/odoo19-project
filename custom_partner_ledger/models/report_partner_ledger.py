# # -*- coding: utf-8 -*-
# import time
# from odoo import api, models, fields, _
# from odoo.exceptions import UserError
#
#
# class ReportPartnerLedgerCustom(models.AbstractModel):
#     _inherit = 'report.accounting_pdf_reports.report_partnerledger'
#     _description = 'Custom Partner Ledger Report'
#
#     def _lines(self, data, partner):
#         """
#         Override the _lines method to add custom functionality
#         """
#         full_account = super()._lines(data, partner)
#         return full_account
#
#     def _sum_partner(self, data, partner, field):
#         """
#         Override the _sum_partner method if needed
#         """
#         result = super()._sum_partner(data, partner, field)
#         return result
#
#     def _get_partner_type_info(self, data, docs):
#         """
#         Determine what type of partners are in the report
#         Returns dict with display information
#         """
#         if not docs:
#             return {
#                 'has_customers': False,
#                 'has_vendors': False,
#                 'display_label': 'Partners',
#                 'count': 0
#             }
#
#         # Get account IDs from the data
#         account_ids = data.get('computed', {}).get('account_ids', [])
#
#         if not account_ids:
#             return {
#                 'has_customers': False,
#                 'has_vendors': False,
#                 'display_label': 'Partners',
#                 'count': len(docs)
#             }
#
#         # Get the accounts
#         accounts = self.env['account.account'].browse(account_ids)
#
#         # Check account types
#         has_receivable = any(acc.account_type == 'asset_receivable' for acc in accounts)
#         has_payable = any(acc.account_type == 'liability_payable' for acc in accounts)
#
#         # Determine display label
#         if has_receivable and has_payable:
#             display_label = 'Customers & Vendors'
#         elif has_receivable:
#             display_label = 'Customers'
#         elif has_payable:
#             display_label = 'Vendors'
#         else:
#             display_label = 'Partners'
#
#         return {
#             'has_customers': has_receivable,
#             'has_vendors': has_payable,
#             'display_label': display_label,
#             'count': len(docs)
#         }
#
#     def _get_partner_label(self, data, partner):
#         """
#         Get the appropriate label for a specific partner (Customer/Vendor)
#         """
#         # Get account IDs from the data
#         account_ids = data.get('computed', {}).get('account_ids', [])
#
#         if not account_ids:
#             return 'Partner'
#
#         # Get move lines for this partner within the selected accounts
#         move_lines = self.env['account.move.line'].search([
#             ('partner_id', '=', partner.id),
#             ('account_id', 'in', account_ids)
#         ], limit=1)
#
#         if move_lines:
#             account_type = move_lines.account_id.account_type
#             if account_type == 'asset_receivable':
#                 return 'Customer'
#             elif account_type == 'liability_payable':
#                 return 'Vendor'
#
#         return 'Partner'
#
#     @api.model
#     def _get_report_values(self, docids, data=None):
#         """
#         Override the main report method to add custom values
#         """
#         # Get parent report values
#         res = super()._get_report_values(docids, data)
#
#         # Get partner type information
#         partner_type_info = self._get_partner_type_info(data, res.get('docs', []))
#
#         # Add custom values to the report context
#         res.update({
#             'custom_title': 'Customized Partner Ledger',
#             'report_date': fields.Date.today(),
#             'partner_type_info': partner_type_info,
#             'get_partner_label': self._get_partner_label,
#         })
#
#         return res
#
#     def _get_partner_opening_balance(self, data, partner):
#         """
#         Calculate opening balance for a partner
#         """
#         query_get_data = self.env['account.move.line'].with_context(
#             data['form'].get('used_context', {})
#         )._query_get()
#
#         reconcile_clause = "" if data['form']['reconciled'] else \
#             ' AND "account_move_line".full_reconcile_id IS NULL '
#
#         date_from = data['form'].get('date_from')
#         date_clause = ""
#         params = [partner.id, tuple(data['computed']['move_state']),
#                   tuple(data['computed']['account_ids'])]
#
#         if date_from:
#             date_clause = ' AND "account_move_line".date < %s '
#             params.append(date_from)
#
#         params.extend(query_get_data[2])
#
#         query = """
#             SELECT
#                 COALESCE(SUM(debit), 0.0) as total_debit,
#                 COALESCE(SUM(credit), 0.0) as total_credit
#             FROM """ + query_get_data[0] + """, account_move AS m
#             WHERE "account_move_line".partner_id = %s
#                 AND m.id = "account_move_line".move_id
#                 AND m.state IN %s
#                 AND account_id IN %s
#                 """ + date_clause + """
#                 AND """ + query_get_data[1] + reconcile_clause
#
#         self.env.cr.execute(query, tuple(params))
#         result = self.env.cr.fetchone()
#
#         if result:
#             return result[0] - result[1]
#         return 0.0


# -*- coding: utf-8 -*-
import time
from odoo import api, models, fields, _
from odoo.exceptions import UserError


class ReportPartnerLedgerCustom(models.AbstractModel):
    _inherit = 'report.accounting_pdf_reports.report_partnerledger'
    _description = 'Custom Partner Ledger Report'

    def _lines(self, data, partner):
        """
        Override the _lines method to add custom functionality
        """
        full_account = super()._lines(data, partner)
        return full_account

    def _sum_partner(self, data, partner, field):
        """
        Override the _sum_partner method if needed
        """
        result = super()._sum_partner(data, partner, field)
        return result

    def _get_partner_type_info(self, data, docs):
        """
        Determine what type of partners are in the report
        Returns dict with display information
        """
        if not docs:
            return {
                'has_customers': False,
                'has_vendors': False,
                'display_label': 'Partners',
                'count': 0
            }

        # Get account IDs from the data
        account_ids = data.get('computed', {}).get('account_ids', [])

        if not account_ids:
            return {
                'has_customers': False,
                'has_vendors': False,
                'display_label': 'Partners',
                'count': len(docs)
            }

        # Get the accounts
        accounts = self.env['account.account'].browse(account_ids)

        # Check account types
        has_receivable = any(acc.account_type == 'asset_receivable' for acc in accounts)
        has_payable = any(acc.account_type == 'liability_payable' for acc in accounts)

        # Determine display label
        if has_receivable and has_payable:
            display_label = 'Customers & Vendors'
        elif has_receivable:
            display_label = 'Customers'
        elif has_payable:
            display_label = 'Vendors'
        else:
            display_label = 'Partners'

        return {
            'has_customers': has_receivable,
            'has_vendors': has_payable,
            'display_label': display_label,
            'count': len(docs)
        }

    def _get_partner_label(self, data, partner):
        """
        Get the appropriate label for a specific partner (Customer/Vendor)
        """
        # Get account IDs from the data
        account_ids = data.get('computed', {}).get('account_ids', [])

        if not account_ids:
            return 'Partner'

        # Get move lines for this partner within the selected accounts
        move_lines = self.env['account.move.line'].search([
            ('partner_id', '=', partner.id),
            ('account_id', 'in', account_ids)
        ], limit=1)

        if move_lines:
            account_type = move_lines.account_id.account_type
            if account_type == 'asset_receivable':
                return 'Customer'
            elif account_type == 'liability_payable':
                return 'Vendor'

        return 'Partner'

    @api.model
    def _get_report_values(self, docids, data=None):
        """
        Override the main report method to add custom values
        """
        # Get parent report values
        res = super()._get_report_values(docids, data)

        # Get partner type information
        partner_type_info = self._get_partner_type_info(data, res.get('docs', []))

        # Get show_details flag from wizard data
        show_details = data.get('form', {}).get('show_details', False)

        # Add custom values to the report context
        res.update({
            'custom_title': 'Customized Partner Ledger',
            'report_date': fields.Date.today(),
            'partner_type_info': partner_type_info,
            'get_partner_label': self._get_partner_label,
            'show_details': show_details,
        })

        return res

    def _get_partner_opening_balance(self, data, partner):
        """
        Calculate opening balance for a partner
        """
        query_get_data = self.env['account.move.line'].with_context(
            data['form'].get('used_context', {})
        )._query_get()

        reconcile_clause = "" if data['form']['reconciled'] else \
            ' AND "account_move_line".full_reconcile_id IS NULL '

        date_from = data['form'].get('date_from')
        date_clause = ""
        params = [partner.id, tuple(data['computed']['move_state']),
                  tuple(data['computed']['account_ids'])]

        if date_from:
            date_clause = ' AND "account_move_line".date < %s '
            params.append(date_from)

        params.extend(query_get_data[2])

        query = """
            SELECT 
                COALESCE(SUM(debit), 0.0) as total_debit,
                COALESCE(SUM(credit), 0.0) as total_credit
            FROM """ + query_get_data[0] + """, account_move AS m
            WHERE "account_move_line".partner_id = %s
                AND m.id = "account_move_line".move_id
                AND m.state IN %s
                AND account_id IN %s
                """ + date_clause + """
                AND """ + query_get_data[1] + reconcile_clause

        self.env.cr.execute(query, tuple(params))
        result = self.env.cr.fetchone()

        if result:
            return result[0] - result[1]
        return 0.0
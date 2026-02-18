# -*- coding: utf-8 -*-
import time
from odoo import api, models, fields, _
from odoo.exceptions import UserError


class ReportPartnerLedgerCustom(models.AbstractModel):
    _inherit = 'report.accounting_pdf_reports.report_partnerledger'
    _description = 'Custom Partner Ledger Report'

    def _lines(self, data, partner):
        """
        Override the _lines method to add custom functionality (due date and PO number)
        """
        full_account = []

        currency = self.env.company.currency_id

        query_get_data = self.env['account.move.line'].with_context(
            data['form'].get('used_context', {})
        )._query_get()

        reconcile_clause = "" if data['form']['reconciled'] else \
            ' AND "account_move_line".full_reconcile_id IS NULL '

        params = [partner.id, tuple(data['computed']['move_state']),
                  tuple(data['computed']['account_ids'])] + query_get_data[2]

        # Get current language
        lang = self.env.context.get('lang') or 'en_US'

        query = """
            SELECT "account_move_line".id, "account_move_line".date, j.code, 
                   COALESCE(acc.name->>%s, acc.name->>'en_US', acc.name::text) as a_name,
                   "account_move_line".ref, m.name as move_name,
                   "account_move_line".name, "account_move_line".debit, 
                   "account_move_line".credit, "account_move_line".amount_currency,
                   "account_move_line".currency_id, c.symbol AS currency_code,
                   m.invoice_date_due, m.client_order_ref as po_number
            FROM """ + query_get_data[0] + """
            LEFT JOIN account_journal j ON ("account_move_line".journal_id = j.id)
            LEFT JOIN account_account acc ON ("account_move_line".account_id = acc.id)
            LEFT JOIN res_currency c ON ("account_move_line".currency_id=c.id)
            LEFT JOIN account_move m ON (m.id="account_move_line".move_id)
            WHERE "account_move_line".partner_id = %s
                AND m.state IN %s
                AND "account_move_line".account_id IN %s AND """ + query_get_data[1] + reconcile_clause + """
            ORDER BY "account_move_line".date
        """

        # Add language parameter at the beginning
        params_with_lang = [lang] + params

        self.env.cr.execute(query, tuple(params_with_lang))
        res = self.env.cr.dictfetchall()

        sum_debit = 0.0
        sum_credit = 0.0

        for r in res:
            sum_debit += r['debit']
            sum_credit += r['credit']

            r['progress'] = sum_debit - sum_credit
            r['displayed_name'] = r['move_name'] if r['move_name'] else ''
            if r['ref']:
                r['displayed_name'] = r['ref'] if not r['displayed_name'] else r['displayed_name'] + ' ' + r['ref']
            if r['name'] and r['name'] != '/':
                r['displayed_name'] = r['name'] if not r['displayed_name'] else r['displayed_name'] + ' ' + r['name']

            # Add due date and PO number to the line
            r['invoice_date_due'] = r['invoice_date_due'] if r['invoice_date_due'] else ''
            r['po_number'] = r['po_number'] if r['po_number'] else ''

            # Currency formatting
            if data['form']['amount_currency'] and r['currency_id']:
                r['currency_id'] = self.env['res.currency'].browse(r['currency_id'])

            full_account.append(r)

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
                'report_title': 'Partner Ledger Report',
                'count': 0
            }

        # Get account IDs from the data
        account_ids = data.get('computed', {}).get('account_ids', [])

        if not account_ids:
            return {
                'has_customers': False,
                'has_vendors': False,
                'display_label': 'Partners',
                'report_title': 'Partner Ledger Report',
                'count': len(docs)
            }

        # Get the accounts
        accounts = self.env['account.account'].browse(account_ids)

        # Check account types
        has_receivable = any(acc.account_type == 'asset_receivable' for acc in accounts)
        has_payable = any(acc.account_type == 'liability_payable' for acc in accounts)

        # Determine display label and report title
        if has_receivable and has_payable:
            display_label = 'Customers & Vendors'
            report_title = 'Customer/Vendor Statement of Report'
        elif has_receivable:
            display_label = 'Customers'
            report_title = 'Customer Statement of Report'
        elif has_payable:
            display_label = 'Vendors'
            report_title = 'Vendor Statement of Report'
        else:
            display_label = 'Partners'
            report_title = 'Partner Ledger Report'

        return {
            'has_customers': has_receivable,
            'has_vendors': has_payable,
            'display_label': display_label,
            'report_title': report_title,
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

        # Add custom values to the report context
        res.update({
            'custom_title': 'Customized Partner Ledger',
            'report_date': fields.Date.today(),
            'partner_type_info': partner_type_info,
            'get_partner_label': self._get_partner_label,
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
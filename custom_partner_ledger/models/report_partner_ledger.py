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
        You can modify the query, add additional fields, or change the logic
        """
        # Call parent method to get original data
        full_account = super()._lines(data, partner)

        # Example customization: Add custom fields or modify existing data
        # for line in full_account:
        #     # Add your custom logic here
        #     # Example: line['custom_field'] = some_value
        #     pass

        return full_account

    def _sum_partner(self, data, partner, field):
        """
        Override the _sum_partner method if needed
        You can add custom calculations or modify the sum logic
        """
        # Call parent method
        result = super()._sum_partner(data, partner, field)

        # Add your custom logic here if needed
        # Example: Apply custom filters or adjustments

        return result

    @api.model
    def _get_report_values(self, docids, data=None):
        """
        Override the main report method to add custom values or logic
        """
        # Get parent report values
        res = super()._get_report_values(docids, data)

        # Add custom values to the report context
        # Example custom additions:
        res.update({
            'custom_title': 'Customized Partner Ledger',
            'report_date': fields.Date.today(),
            # Add any other custom values you need in the template
        })

        return res

    def _get_partner_opening_balance(self, data, partner):
        """
        Example: Add a new method to calculate opening balance
        This is a custom method you can call from your template
        """
        query_get_data = self.env['account.move.line'].with_context(
            data['form'].get('used_context', {})
        )._query_get()

        reconcile_clause = "" if data['form']['reconciled'] else \
            ' AND "account_move_line".full_reconcile_id IS NULL '

        # Build date filter for opening balance
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
            return result[0] - result[1]  # debit - credit
        return 0.0
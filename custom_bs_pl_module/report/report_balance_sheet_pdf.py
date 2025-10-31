# -*- coding: utf-8 -*-
from odoo import models, api
import json
import logging

_logger = logging.getLogger(__name__)


class ReportBalanceSheetPDF(models.AbstractModel):
    _name = 'report.custom_bs_pl_module.report_balance_sheet_pdf'
    _description = 'Custom Balance Sheet PDF Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Include warehouse analytic breakdown + combined totals in PDF"""

        docs = self.env['account.balance.report'].browse(docids)
        data = data or {}

        all_warehouse_data = []
        combined_totals = {'debit': 0.0, 'credit': 0.0, 'balance': 0.0}

        for doc in docs:
            _logger.info("=" * 80)
            _logger.info("🔍 DEBUG: Processing Balance Sheet Report")
            _logger.info(f"Company: {doc.company_id.name}")
            _logger.info(f"Date From: {doc.date_from}")
            _logger.info(f"Date To: {doc.date_to}")

            # Check if warehouse analytics are selected
            if hasattr(doc, 'warehouse_analytic_ids') and doc.warehouse_analytic_ids:
                _logger.info(f"✅ Warehouse Analytic Accounts Selected: {len(doc.warehouse_analytic_ids)}")

                for analytic in doc.warehouse_analytic_ids:
                    _logger.info(f"\n📦 Processing Warehouse: {analytic.name} (ID: {analytic.id})")

                    # First, let's check if ANY data exists with this analytic
                    check_query = """
                        SELECT COUNT(*) as count
                        FROM account_move_line aml
                        WHERE aml.analytic_distribution IS NOT NULL
                          AND aml.analytic_distribution::text LIKE %s
                    """
                    self.env.cr.execute(check_query, (f'%"{analytic.id}"%',))
                    check_result = self.env.cr.fetchone()
                    _logger.info(f"   Found {check_result[0]} move lines with this analytic")

                    # Main query with analytic_distribution
                    query = """
                        SELECT
                            SUM(aml.debit) AS debit,
                            SUM(aml.credit) AS credit,
                            SUM(aml.debit - aml.credit) AS balance,
                            COUNT(*) as line_count
                        FROM account_move_line aml
                        JOIN account_move am ON aml.move_id = am.id
                        JOIN account_account aa ON aml.account_id = aa.id
                        WHERE am.state = 'posted'
                          AND aml.company_id = %s
                          AND aml.analytic_distribution IS NOT NULL
                          AND aml.analytic_distribution::text LIKE %s
                    """

                    params = [doc.company_id.id, f'%"{analytic.id}"%']

                    # Add date filters conditionally
                    if doc.date_from:
                        query += " AND aml.date >= %s"
                        params.append(doc.date_from)

                    if doc.date_to:
                        query += " AND aml.date <= %s"
                        params.append(doc.date_to)

                    # Filter only Balance Sheet accounts
                    query += """
                        AND aa.account_type IN (
                            'asset_receivable', 'asset_cash', 'asset_current', 
                            'asset_non_current', 'asset_prepayments', 'asset_fixed',
                            'liability_payable', 'liability_credit_card', 
                            'liability_current', 'liability_non_current',
                            'equity', 'equity_unaffected'
                        )
                    """

                    _logger.info(f"   Executing query with params: {params}")
                    self.env.cr.execute(query, tuple(params))
                    row = self.env.cr.dictfetchone() or {}

                    _logger.info(
                        f"   Results: Debit={row.get('debit')}, Credit={row.get('credit')}, Balance={row.get('balance')}, Lines={row.get('line_count')}")

                    warehouse_data = {
                        'warehouse_name': analytic.name,
                        'debit': row.get('debit', 0.0) or 0.0,
                        'credit': row.get('credit', 0.0) or 0.0,
                        'balance': row.get('balance', 0.0) or 0.0,
                    }
                    all_warehouse_data.append(warehouse_data)

                    # Accumulate totals
                    combined_totals['debit'] += warehouse_data['debit']
                    combined_totals['credit'] += warehouse_data['credit']
                    combined_totals['balance'] += warehouse_data['balance']
            else:
                _logger.info("⚠️ No Warehouse Analytic Accounts Selected - Showing All")

                # No analytics selected → Show combined data for all warehouses
                query = """
                    SELECT
                        SUM(aml.debit) AS debit,
                        SUM(aml.credit) AS credit,
                        SUM(aml.debit - aml.credit) AS balance
                    FROM account_move_line aml
                    JOIN account_move am ON aml.move_id = am.id
                    JOIN account_account aa ON aml.account_id = aa.id
                    WHERE am.state = 'posted'
                      AND aml.company_id = %s
                """

                params = [doc.company_id.id]

                if doc.date_from:
                    query += " AND aml.date >= %s"
                    params.append(doc.date_from)

                if doc.date_to:
                    query += " AND aml.date <= %s"
                    params.append(doc.date_to)

                query += """
                    AND aa.account_type IN (
                        'asset_receivable', 'asset_cash', 'asset_current', 
                        'asset_non_current', 'asset_prepayments', 'asset_fixed',
                        'liability_payable', 'liability_credit_card', 
                        'liability_current', 'liability_non_current',
                        'equity', 'equity_unaffected'
                    )
                """

                self.env.cr.execute(query, tuple(params))
                row = self.env.cr.dictfetchone() or {}

                all_warehouse_data.append({
                    'warehouse_name': 'All Warehouses',
                    'debit': row.get('debit', 0.0) or 0.0,
                    'credit': row.get('credit', 0.0) or 0.0,
                    'balance': row.get('balance', 0.0) or 0.0,
                })

                combined_totals['debit'] = row.get('debit', 0.0) or 0.0
                combined_totals['credit'] = row.get('credit', 0.0) or 0.0
                combined_totals['balance'] = row.get('balance', 0.0) or 0.0

        _logger.info("\n📊 Final Warehouse Data:")
        for wh in all_warehouse_data:
            _logger.info(
                f"   {wh['warehouse_name']}: Debit={wh['debit']}, Credit={wh['credit']}, Balance={wh['balance']}")
        _logger.info(f"📊 Combined Totals: {combined_totals}")
        _logger.info("=" * 80)

        # Update data dictionary for template
        data.update({
            'all_warehouse_data': all_warehouse_data,
            'combined_totals': combined_totals,
        })

        return {
            'doc_ids': docids,
            'doc_model': 'account.balance.report',
            'docs': docs,
            'data': data,
        }
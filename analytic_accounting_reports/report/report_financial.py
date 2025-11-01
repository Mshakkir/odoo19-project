from odoo import api, models
import json


class ReportFinancial(models.AbstractModel):
    _inherit = 'report.accounting_pdf_reports.report_financial'

    def _compute_account_balance(self, accounts):
        """Override to add analytic distribution filtering"""
        mapping = {
            'balance': "COALESCE(SUM(debit),0) - COALESCE(SUM(credit), 0) as balance",
            'debit': "COALESCE(SUM(debit), 0) as debit",
            'credit': "COALESCE(SUM(credit), 0) as credit",
        }

        res = {}
        for account in accounts:
            res[account.id] = dict.fromkeys(mapping, 0.0)

        if accounts:
            tables, where_clause, where_params = self.env['account.move.line']._query_get()
            tables = tables.replace('"', '') if tables else "account_move_line"
            wheres = [""]

            if where_clause.strip():
                wheres.append(where_clause.strip())

            # Add analytic distribution filtering for selected warehouses
            analytic_account_ids = self.env.context.get('analytic_account_ids', [])
            if analytic_account_ids:
                # Build OR condition for multiple analytic accounts
                analytic_conditions = []
                for analytic_id in analytic_account_ids:
                    analytic_conditions.append(
                        f"(analytic_distribution::text LIKE '%\"{analytic_id}\"%' OR "
                        f"analytic_distribution::text LIKE '%\"{analytic_id}\":%')"
                    )
                if analytic_conditions:
                    wheres.append("(" + " OR ".join(analytic_conditions) + ")")

            filters = " AND ".join(wheres)
            request = "SELECT account_id as id, " + ', '.join(mapping.values()) + \
                      " FROM " + tables + \
                      " WHERE account_id IN %s " + filters + \
                      " GROUP BY account_id"
            params = (tuple(accounts._ids),) + tuple(where_params)
            self.env.cr.execute(request, params)
            for row in self.env.cr.dictfetchall():
                res[row['id']] = row

        return res

    def _get_warehouse_breakdown(self, accounts):
        """Get balance breakdown by warehouse for the accounts"""
        if not accounts:
            return {}, []

        # Get selected warehouses or all SSAQCO warehouses
        analytic_account_ids = self.env.context.get('analytic_account_ids', [])

        if analytic_account_ids:
            # Use selected warehouses
            warehouses = self.env['account.analytic.account'].browse(analytic_account_ids)
        else:
            # Get all SSAQCO warehouses
            warehouses = self.env['account.analytic.account'].search([
                ('name', 'ilike', 'SSAQCO')
            ], order='name')

        if not warehouses:
            return {}, []

        result = {}
        for account in accounts:
            result[account.id] = {}
            for warehouse in warehouses:
                result[account.id][warehouse.id] = {
                    'balance': 0.0,
                    'debit': 0.0,
                    'credit': 0.0,
                    'name': warehouse.name
                }

        tables, where_clause, where_params = self.env['account.move.line']._query_get()
        tables = tables.replace('"', '') if tables else "account_move_line"

        for warehouse in warehouses:
            wheres = [""]
            if where_clause.strip():
                wheres.append(where_clause.strip())

            # Filter by this warehouse's analytic account
            wheres.append(
                f"(analytic_distribution::text LIKE '%\"{warehouse.id}\"%' OR "
                f"analytic_distribution::text LIKE '%\"{warehouse.id}\":%')"
            )

            filters = " AND ".join(wheres)

            request = """
                SELECT account_id, 
                       COALESCE(SUM(debit), 0) as debit,
                       COALESCE(SUM(credit), 0) as credit,
                       COALESCE(SUM(debit), 0) - COALESCE(SUM(credit), 0) as balance
                FROM """ + tables + """
                WHERE account_id IN %s """ + filters + """
                GROUP BY account_id
            """
            params = (tuple(accounts._ids),) + tuple(where_params)
            self.env.cr.execute(request, params)

            for row in self.env.cr.dictfetchall():
                if row['account_id'] in result:
                    result[row['account_id']][warehouse.id] = {
                        'balance': row['balance'],
                        'debit': row['debit'],
                        'credit': row['credit'],
                        'name': warehouse.name
                    }

        return result, warehouses

    @api.model
    def _get_report_values(self, docids, data=None):
        """Override to pass analytic information"""
        result = super(ReportFinancial, self)._get_report_values(docids, data)

        # Get selected warehouse names
        warehouse_names = []
        if data and data.get('form', {}).get('analytic_account_ids'):
            analytic_data = data['form']['analytic_account_ids']
            # Handle many2many format: [(6, 0, [id1, id2, id3])]
            analytic_ids = []
            if analytic_data and isinstance(analytic_data[0], (list, tuple)):
                analytic_ids = analytic_data[0][2] if len(analytic_data[0]) > 2 else []
            else:
                analytic_ids = analytic_data

            if analytic_ids:
                analytic_accounts = self.env['account.analytic.account'].browse(analytic_ids)
                warehouse_names = [acc.name for acc in analytic_accounts]
                result['selected_warehouses'] = analytic_accounts
            else:
                result['selected_warehouses'] = False
        else:
            result['selected_warehouses'] = False

        # Set display text
        if warehouse_names:
            if len(warehouse_names) == 1:
                result['warehouse_display'] = warehouse_names[0]
            else:
                result['warehouse_display'] = ', '.join(warehouse_names)
        else:
            result['warehouse_display'] = 'All Warehouses'

        # Add combined column flag
        if data and data.get('form'):
            result['include_combined'] = data['form'].get('include_combined', False)

        return result
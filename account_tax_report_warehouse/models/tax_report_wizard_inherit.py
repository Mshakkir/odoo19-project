from odoo import models, fields, api


class AccountTaxReportWizard(models.TransientModel):
    _inherit = 'account.tax.report.wizard'

    detail_line_ids = fields.One2many(
        'tax.report.detail.line',
        'wizard_id',
        string='Tax Summary Lines'
    )

    def _sql_from_amls_one(self):
        """Get tax amounts from tax lines"""
        sql = """
            SELECT account_move_line.tax_line_id,
                   COALESCE(SUM(account_move_line.debit - account_move_line.credit), 0)
            FROM %s
            WHERE %s AND account_move_line.tax_line_id IS NOT NULL
            GROUP BY account_move_line.tax_line_id
        """
        return sql

    def _sql_from_amls_two(self):
        """Get base amounts from invoice lines with taxes"""
        sql = """
            SELECT r.account_tax_id,
                   COALESCE(SUM(account_move_line.debit - account_move_line.credit), 0)
            FROM %s
            INNER JOIN account_move_line_account_tax_rel r
                ON (account_move_line.id = r.account_move_line_id)
            INNER JOIN account_tax t ON (r.account_tax_id = t.id)
            WHERE %s
            GROUP BY r.account_tax_id
        """
        return sql

    def _get_move_ids_for_tax(self, tax_id, tax_type):
        """Get move IDs for a specific tax, filtered by analytic accounts if needed"""
        domain = [
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
            ('state', '=', 'posted')
        ]

        if tax_type == 'sale':
            domain.append(('move_type', 'in', ['out_invoice', 'out_refund']))
        else:
            domain.append(('move_type', 'in', ['in_invoice', 'in_refund']))

        moves = self.env['account.move'].search(domain)
        tax_moves = moves.filtered(
            lambda m: tax_id in m.invoice_line_ids.mapped('tax_ids').ids
        )

        # Filter by analytic accounts if selected
        if self.analytic_account_ids:
            filtered_moves = self.env['account.move']
            for move in tax_moves:
                for line in move.invoice_line_ids:
                    if line.analytic_distribution:
                        analytic_ids_in_line = [int(k) for k in line.analytic_distribution.keys()]
                        if any(acc_id in analytic_ids_in_line for acc_id in self.analytic_account_ids.ids):
                            filtered_moves |= move
                            break
            return filtered_moves.ids

        return tax_moves.ids

    def compute_tax_summary(self):
        self.ensure_one()
        TaxLine = self.env['tax.report.detail.line']
        self.detail_line_ids.unlink()

        # Prepare taxes dictionary
        taxes = {}
        for tax in self.env['account.tax'].search([('type_tax_use', '!=', 'none')]):
            if tax.children_tax_ids:
                for child in tax.children_tax_ids:
                    if child.type_tax_use == 'none':
                        continue
                    taxes[child.id] = {
                        'tax': 0,
                        'net': 0,
                        'name': child.name,
                        'type': tax.type_tax_use,
                        'tax_id': child.id,
                    }
            else:
                taxes[tax.id] = {
                    'tax': 0,
                    'net': 0,
                    'name': tax.name,
                    'type': tax.type_tax_use,
                    'tax_id': tax.id,
                }

        # Build query context
        context = self.env.context.copy()
        context.update({
            'date_from': self.date_from,
            'date_to': self.date_to,
            'state': 'posted',
            'strict_range': True,
        })

        # ✅ FIXED: Apply analytic filter differently for tax lines vs invoice lines
        if self.analytic_account_ids:
            # Step 1: Get move IDs that have lines with the selected analytic accounts
            self.env.cr.execute("""
                SELECT DISTINCT aml.move_id
                FROM account_move_line aml
                JOIN account_move am ON am.id = aml.move_id
                WHERE am.invoice_date >= %s
                  AND am.invoice_date <= %s
                  AND am.state = 'posted'
                  AND (""" + " OR ".join(
                [f"aml.analytic_distribution ? '{aid}'" for aid in self.analytic_account_ids.ids]
            ) + ")", (self.date_from, self.date_to))

            filtered_move_ids = [row[0] for row in self.env.cr.fetchall()]

            if not filtered_move_ids:
                # No moves match the filter - return empty report
                return self._create_empty_summary()

            # Get base query components
            tables, where_clause, where_params = self.env['account.move.line'].with_context(context)._query_get()

            # Add move_id filter for BOTH tax and base queries
            move_filter = f" AND account_move_line.move_id IN ({','.join(map(str, filtered_move_ids))})"
            where_clause += move_filter

        else:
            # No analytic filter - use standard query
            tables, where_clause, where_params = self.env['account.move.line'].with_context(context)._query_get()

        # --- 1️⃣ Compute Tax Amounts (from tax lines) ---
        sql = self._sql_from_amls_one()
        query = sql % (tables, where_clause)
        self.env.cr.execute(query, where_params)
        results = self.env.cr.fetchall()
        for result in results:
            if result[0] in taxes:
                taxes[result[0]]['tax'] = abs(result[1])

        # --- 2️⃣ Compute Base (Net) Amounts (from invoice lines) ---
        sql2 = self._sql_from_amls_two()
        query = sql2 % (tables, where_clause)
        self.env.cr.execute(query, where_params)
        results = self.env.cr.fetchall()
        for result in results:
            if result[0] in taxes:
                taxes[result[0]]['net'] = abs(result[1])

        # --- Rest of the code remains the same ---
        return self._create_tax_summary_lines(taxes)

    def _create_empty_summary(self):
        """Create empty summary when no data matches filter"""
        TaxLine = self.env['tax.report.detail.line']
        TaxLine.create({
            'wizard_id': self.id,
            'tax_name': 'Total Sales',
            'base_amount': 0.0,
            'tax_amount': 0.0,
            'is_summary_row': True,
            'sequence': 10,
        })
        TaxLine.create({
            'wizard_id': self.id,
            'tax_name': 'Total Purchases',
            'base_amount': 0.0,
            'tax_amount': 0.0,
            'is_summary_row': True,
            'sequence': 20,
        })
        TaxLine.create({
            'wizard_id': self.id,
            'tax_name': 'Net VAT Due',
            'base_amount': 0.0,
            'tax_amount': 0.0,
            'is_summary_row': True,
            'sequence': 30,
        })

    def _create_tax_summary_lines(self, taxes):
        """Create detail lines from taxes dictionary"""
        TaxLine = self.env['tax.report.detail.line']

        groups = {'sale': [], 'purchase': []}
        for tax in taxes.values():
            if tax['tax'] or tax['net']:
                groups[tax['type']].append(tax)

        sequence = 10
        total_sales_base = total_sales_tax = 0.0
        total_purchase_base = total_purchase_tax = 0.0

        # --- Sales ---
        for tax in groups['sale']:
            move_ids = self._get_move_ids_for_tax(tax['tax_id'], 'sale')
            TaxLine.create({
                'wizard_id': self.id,
                'type': 'sale',
                'tax_id': tax['tax_id'],
                'tax_name': tax['name'],
                'base_amount': tax['net'],
                'tax_amount': tax['tax'],
                'move_ids': [(6, 0, move_ids)],
                'is_summary_row': False,
                'sequence': sequence,
            })
            total_sales_base += tax['net']
            total_sales_tax += tax['tax']
            sequence += 10

        # --- Total Sales Row ---
        TaxLine.create({
            'wizard_id': self.id,
            'type': 'sale',
            'tax_name': 'Total Sales',
            'base_amount': total_sales_base,
            'tax_amount': total_sales_tax,
            'is_summary_row': True,
            'sequence': sequence,
        })
        sequence += 10

        # --- Purchases ---
        for tax in groups['purchase']:
            move_ids = self._get_move_ids_for_tax(tax['tax_id'], 'purchase')
            TaxLine.create({
                'wizard_id': self.id,
                'type': 'purchase',
                'tax_id': tax['tax_id'],
                'tax_name': tax['name'],
                'base_amount': tax['net'],
                'tax_amount': tax['tax'],
                'move_ids': [(6, 0, move_ids)],
                'is_summary_row': False,
                'sequence': sequence,
            })
            total_purchase_base += tax['net']
            total_purchase_tax += tax['tax']
            sequence += 10

        # --- Total Purchases Row ---
        TaxLine.create({
            'wizard_id': self.id,
            'type': 'purchase',
            'tax_name': 'Total Purchases',
            'base_amount': total_purchase_base,
            'tax_amount': total_purchase_tax,
            'is_summary_row': True,
            'sequence': sequence,
        })
        sequence += 10

        # --- Net VAT Due Row ---
        net_vat_due = total_sales_tax - total_purchase_tax
        TaxLine.create({
            'wizard_id': self.id,
            'tax_name': 'Net VAT Due',
            'base_amount': 0.0,
            'tax_amount': net_vat_due,
            'is_summary_row': True,
            'sequence': sequence,
        })

    def open_tax_report_details(self):
        self.compute_tax_summary()
        return {
            'name': 'Tax Report Summary',
            'type': 'ir.actions.act_window',
            'res_model': 'tax.report.detail.line',
            'view_mode': 'list,form',
            'target': 'current',
            'context': {'default_wizard_id': self.id},
            'domain': [('wizard_id', '=', self.id)],
        }
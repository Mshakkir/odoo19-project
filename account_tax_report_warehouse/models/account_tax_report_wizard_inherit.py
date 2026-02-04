# from odoo import api, fields, models
#
#
# class AccountTaxReportWizard(models.TransientModel):
#     _inherit = "account.tax.report.wizard"
#
#     analytic_account_ids = fields.Many2many(
#         'account.analytic.account',
#         string="Analytic Accounts (Warehouses)",
#         help="Filter Tax Report based on selected warehouse analytic accounts."
#     )
#
#     def _print_report(self, data=None):
#         """Override to pass analytic filter to report."""
#         if data is None:
#             data = {}
#
#         form_data = self.read(['date_from', 'date_to', 'target_move', 'analytic_account_ids'])[0]
#
#         # Normalize analytic_account_ids
#         analytic_ids = form_data.get('analytic_account_ids', [])
#         if analytic_ids and isinstance(analytic_ids[0], (tuple, list)):
#             analytic_ids = analytic_ids[0][2]  # get IDs from [(6, 0, [ids])]
#         form_data['analytic_account_ids'] = analytic_ids
#
#         # Merge with existing data
#         data.update({'form': form_data})
#
#         return self.env.ref('accounting_pdf_reports.action_report_account_tax').report_action(
#             self, data=data
#         )
#
#
# class ReportTax(models.AbstractModel):
#     _inherit = 'report.accounting_pdf_reports.report_tax'
#
#     def _compute_from_amls(self, options, taxes):
#         """Override to add analytic account filtering."""
#         import logging
#         _logger = logging.getLogger(__name__)
#
#         analytic_ids = options.get('analytic_account_ids', [])
#
#         if not analytic_ids:
#             # No filter - use parent method
#             return super()._compute_from_amls(options, taxes)
#
#         _logger.info(f"=== ANALYTIC FILTER IN _compute_from_amls ===")
#         _logger.info(f"Filtering by analytic accounts: {analytic_ids}")
#
#         # Compute tax amounts with analytic filter
#         sql = self._sql_from_amls_one()
#         tables, where_clause, where_params = self.env['account.move.line']._query_get()
#
#         # Add analytic distribution filter
#         # In Odoo 19, analytic_distribution is JSON: {"account_id": percentage}
#         # We need to check if any of our analytic_ids exist in the JSON keys
#         analytic_filter = " AND ("
#         analytic_conditions = []
#         for analytic_id in analytic_ids:
#             analytic_conditions.append(f"account_move_line.analytic_distribution ? '{analytic_id}'")
#         analytic_filter += " OR ".join(analytic_conditions)
#         analytic_filter += ")"
#
#         where_clause += analytic_filter
#
#         # Execute query for tax amounts
#         query = sql % (tables, where_clause)
#         _logger.info(f"Tax amount query: {query}")
#         _logger.info(f"Query params: {where_params}")
#
#         self.env.cr.execute(query, where_params)
#         results = self.env.cr.fetchall()
#
#         _logger.info(f"Tax amount results count: {len(results)}")
#
#         for result in results:
#             if result[0] in taxes:
#                 taxes[result[0]]['tax'] = abs(result[1])
#                 _logger.info(f"  Tax ID {result[0]}: tax amount = {abs(result[1])}")
#
#         # Compute net amounts (base) with analytic filter
#         sql2 = self._sql_from_amls_two()
#         query = sql2 % (tables, where_clause)
#
#         self.env.cr.execute(query, where_params)
#         results = self.env.cr.fetchall()
#
#         _logger.info(f"Base amount results count: {len(results)}")
#
#         for result in results:
#             if result[0] in taxes:
#                 taxes[result[0]]['net'] = abs(result[1])
#                 _logger.info(f"  Tax ID {result[0]}: base amount = {abs(result[1])}")
#
#         _logger.info(f"=== END ANALYTIC FILTER ===")

from odoo import models, fields, api
import base64
import io
from datetime import datetime

try:
    import xlsxwriter
except ImportError:
    import logging

    _logger = logging.getLogger(__name__)
    _logger.warning('xlsxwriter not installed. Excel export will not work.')


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

    def export_tax_report_excel(self):
        """Export tax report to Excel"""
        self.ensure_one()

        # Ensure tax summary lines exist
        if not self.detail_line_ids:
            self.compute_tax_summary()

        # Create Excel file in memory
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Tax Report')

        # Define formats
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#4472C4',
            'font_color': 'white',
        })

        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D3D3D3',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })

        summary_format = workbook.add_format({
            'bold': True,
            'bg_color': '#FFFF00',
            'border': 1,
            'num_format': '#,##0.00'
        })

        number_format = workbook.add_format({
            'num_format': '#,##0.00',
            'border': 1
        })

        text_format = workbook.add_format({
            'border': 1
        })

        text_center_format = workbook.add_format({
            'border': 1,
            'align': 'center'
        })

        # Set column widths
        worksheet.set_column('A:A', 20)  # Type
        worksheet.set_column('B:B', 40)  # Tax Name
        worksheet.set_column('C:C', 20)  # Base Amount
        worksheet.set_column('D:D', 20)  # Tax Amount

        # Write title
        if self.analytic_account_ids:
            analytic_names = ', '.join(self.analytic_account_ids.mapped('name'))
            title = f'Tax Report - {analytic_names}'
        else:
            title = 'Tax Report - All Warehouses'

        worksheet.merge_range('A1:D1', title, title_format)

        # Write date range
        date_range = f"From {self.date_from.strftime('%d/%m/%Y')} To {self.date_to.strftime('%d/%m/%Y')}"
        worksheet.merge_range('A2:D2', date_range, workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'italic': True
        }))

        # Write company info
        company_name = self.env.company.name
        worksheet.merge_range('A3:D3', company_name, workbook.add_format({
            'align': 'center',
            'valign': 'vcenter'
        }))

        row = 4

        # Write headers
        worksheet.write(row, 0, 'Type', header_format)
        worksheet.write(row, 1, 'Tax Name', header_format)
        worksheet.write(row, 2, 'Base Amount', header_format)
        worksheet.write(row, 3, 'Tax Amount', header_format)

        row += 1

        # Write data - ordered by sequence
        lines = self.detail_line_ids.sorted(key=lambda l: l.sequence)

        for line in lines:
            # Determine format
            if line.is_summary_row:
                current_text_format = summary_format
                current_number_format = summary_format
            else:
                current_text_format = text_format
                current_number_format = number_format

            # Write type
            type_display = ''
            if line.type == 'sale':
                type_display = 'Sales'
            elif line.type == 'purchase':
                type_display = 'Purchase'

            worksheet.write(row, 0, type_display, current_text_format)
            worksheet.write(row, 1, line.tax_name or '', current_text_format)
            worksheet.write(row, 2, line.base_amount, current_number_format)
            worksheet.write(row, 3, line.tax_amount, current_number_format)

            row += 1

        workbook.close()
        output.seek(0)
        excel_data = output.read()
        output.close()

        # Generate filename
        filename = f'Tax_Report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'

        # Create attachment
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(excel_data),
            'store_fname': filename,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        # Return download action
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
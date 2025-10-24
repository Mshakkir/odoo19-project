# from odoo import api, models, _
# from odoo.exceptions import UserError
#
#
# class ReportTax(models.AbstractModel):
#     _name = 'report.accounting_pdf_reports.report_tax'
#     _description = 'Tax Report'
#
#     @api.model
#     def _get_report_values(self, docids, data=None):
#         if not data.get('form'):
#             raise UserError(_("Form content is missing, this report cannot be printed."))
#         return {
#             'data': data['form'],
#             'lines': self.get_lines(data.get('form')),
#         }
#
#
#     def _sql_from_amls_one(self):
#         sql = """SELECT "account_move_line".tax_line_id, COALESCE(SUM("account_move_line".debit-"account_move_line".credit), 0)
#                     FROM %s
#                     WHERE %s GROUP BY "account_move_line".tax_line_id"""
#         return sql
#
#     def _sql_from_amls_two(self):
#         sql = """SELECT r.account_tax_id, COALESCE(SUM("account_move_line".debit-"account_move_line".credit), 0)
#                  FROM %s
#                  INNER JOIN account_move_line_account_tax_rel r ON ("account_move_line".id = r.account_move_line_id)
#                  INNER JOIN account_tax t ON (r.account_tax_id = t.id)
#                  WHERE %s GROUP BY r.account_tax_id"""
#         return sql
#
#     def _compute_from_amls(self, options, taxes):
#         #compute the tax amount
#         sql = self._sql_from_amls_one()
#         tables, where_clause, where_params = self.env['account.move.line']._query_get()
#         query = sql % (tables, where_clause)
#         self.env.cr.execute(query, where_params)
#         results = self.env.cr.fetchall()
#         for result in results:
#             if result[0] in taxes:
#                 taxes[result[0]]['tax'] = abs(result[1])
#
#         #compute the net amount
#         sql2 = self._sql_from_amls_two()
#         query = sql2 % (tables, where_clause)
#         self.env.cr.execute(query, where_params)
#         results = self.env.cr.fetchall()
#         for result in results:
#             if result[0] in taxes:
#                 taxes[result[0]]['net'] = abs(result[1])
#
#     @api.model
#     def get_lines(self, options):
#         taxes = {}
#         for tax in self.env['account.tax'].search([('type_tax_use', '!=', 'none')]):
#             if tax.children_tax_ids:
#                 for child in tax.children_tax_ids:
#                     if child.type_tax_use != 'none':
#                         continue
#                     taxes[child.id] = {'tax': 0, 'net': 0, 'name': child.name, 'type': tax.type_tax_use}
#             else:
#                 taxes[tax.id] = {'tax': 0, 'net': 0, 'name': tax.name, 'type': tax.type_tax_use}
#         self.with_context(date_from=options['date_from'], date_to=options['date_to'],
#                           state=options['target_move'],
#                           strict_range=True)._compute_from_amls(options, taxes)
#         groups = dict((tp, []) for tp in ['sale', 'purchase'])
#         for tax in taxes.values():
#             # Include taxes that have either tax amount OR base (net) amount
#             if tax['tax'] or tax['net']:
#                 groups[tax['type']].append(tax)
#         return groups
from odoo import api, models, _
from odoo.exceptions import UserError


class ReportTax(models.AbstractModel):
    _name = 'report.accounting_pdf_reports.report_tax'
    _description = 'Tax Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form'):
            raise UserError(_("Form content is missing, this report cannot be printed."))

        # Handle analytic accounts for warehouse filtering
        analytic_accounts = []
        context = data['form'].get('used_context') or {}

        if data['form'].get('analytic_account_ids'):
            analytic_account_ids = self.env['account.analytic.account'].browse(
                data['form'].get('analytic_account_ids')
            )
            context['analytic_account_ids'] = analytic_account_ids
            analytic_accounts = [account.name for account in analytic_account_ids]

        return {
            'data': data['form'],
            'lines': self.with_context(context).get_lines(data.get('form')),
            'analytic_accounts': analytic_accounts,
        }

    def _sql_from_amls_one(self):
        sql = """SELECT "account_move_line".tax_line_id, COALESCE(SUM("account_move_line".debit-"account_move_line".credit), 0)
                    FROM %s
                    WHERE %s GROUP BY "account_move_line".tax_line_id"""
        return sql

    def _sql_from_amls_two(self):
        sql = """SELECT r.account_tax_id, COALESCE(SUM("account_move_line".debit-"account_move_line".credit), 0)
                 FROM %s
                 INNER JOIN account_move_line_account_tax_rel r ON ("account_move_line".id = r.account_move_line_id)
                 INNER JOIN account_tax t ON (r.account_tax_id = t.id)
                 WHERE %s GROUP BY r.account_tax_id"""
        return sql

    def _compute_from_amls(self, options, taxes):
        # Get base query components
        tables, where_clause, where_params = self.env['account.move.line']._query_get()
        tables = tables.replace('"', '')
        if not tables:
            tables = 'account_move_line'

        # ✅ FIX: Analytic filter using subquery (Odoo 19+ compatible)
        analytic_account_ids = self.env.context.get('analytic_account_ids')
        analytic_filter = ""
        analytic_params = ()

        if analytic_account_ids:
            analytic_filter = (
                " AND (account_move_line.move_id IN (SELECT move_id FROM account_analytic_line WHERE account_id IN %s)"
                " OR account_move_line.move_id NOT IN (SELECT move_id FROM account_analytic_line))"
            )
            analytic_params = (tuple(a.id for a in analytic_account_ids),)

        # Build complete where clause
        wheres = [""]
        if where_clause.strip():
            wheres.append(where_clause.strip())
        filters = " AND ".join(wheres)

        # Compute the tax amount
        sql = self._sql_from_amls_one()
        query = sql % (tables, filters + analytic_filter)
        params = tuple(where_params) + analytic_params
        self.env.cr.execute(query, params)
        results = self.env.cr.fetchall()
        for result in results:
            if result[0] in taxes:
                taxes[result[0]]['tax'] = abs(result[1])

        # Compute the net amount
        sql2 = self._sql_from_amls_two()
        query = sql2 % (tables, filters + analytic_filter)
        self.env.cr.execute(query, params)
        results = self.env.cr.fetchall()
        for result in results:
            if result[0] in taxes:
                taxes[result[0]]['net'] = abs(result[1])

    @api.model
    def get_lines(self, options):
        taxes = {}
        for tax in self.env['account.tax'].search([('type_tax_use', '!=', 'none')]):
            if tax.children_tax_ids:
                for child in tax.children_tax_ids:
                    if child.type_tax_use != 'none':
                        continue
                    taxes[child.id] = {'tax': 0, 'net': 0, 'name': child.name, 'type': tax.type_tax_use}
            else:
                taxes[tax.id] = {'tax': 0, 'net': 0, 'name': tax.name, 'type': tax.type_tax_use}

        self.with_context(
            date_from=options['date_from'],
            date_to=options['date_to'],
            state=options['target_move'],
            strict_range=True
        )._compute_from_amls(options, taxes)

        groups = dict((tp, []) for tp in ['sale', 'purchase'])
        for tax in taxes.values():
            # Include taxes that have either tax amount OR base (net) amount
            if tax['tax'] or tax['net']:
                groups[tax['type']].append(tax)
        return groups
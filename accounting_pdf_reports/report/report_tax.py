# from odoo import api, models, _
# from odoo.exceptions import UserError
#
#
# # class ReportTax(models.AbstractModel):
# #     _name = 'report.accounting_pdf_reports.report_tax'
# #     _description = 'Tax Report'
# #
# #     @api.model
# #     def _get_report_values(self, docids, data=None):
# #         if not data.get('form'):
# #             raise UserError(_("Form content is missing, this report cannot be printed."))
# #         return {
# #             'data': data['form'],
# #             'lines': self.get_lines(data.get('form')),
# #         }
# class ReportTax(models.AbstractModel):
#     _name = 'report.accounting_pdf_reports.report_tax'
#     _description = 'Tax Report'
#
#     @api.model
#     def _get_report_values(self, docids, data=None):
#         if not data.get('form'):
#             raise UserError(_("Form content is missing, this report cannot be printed."))
#
#         options = data['form']
#         lines = self.get_lines(options)
#         report_type = 'detailed' if options.get('detailed_summary') else 'normal'
#
#         return {
#             'data': options,
#             'lines': lines,
#             'report_type': report_type,
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

        options = data['form']
        lines = self.get_lines(options)
        report_type = 'detailed' if options.get('detailed_summary') else 'normal'

        return {
            'data': options,
            'lines': lines,
            'report_type': report_type,
        }

    # ---------- SQL Helpers ----------
    def _sql_from_amls_one(self):
        sql = """SELECT "account_move_line".tax_line_id, COALESCE(SUM("account_move_line".debit - "account_move_line".credit), 0)
                 FROM %s
                 WHERE %s GROUP BY "account_move_line".tax_line_id"""
        return sql

    def _sql_from_amls_two(self):
        sql = """SELECT r.account_tax_id, COALESCE(SUM("account_move_line".debit - "account_move_line".credit), 0)
                 FROM %s
                 INNER JOIN account_move_line_account_tax_rel r ON ("account_move_line".id = r.account_move_line_id)
                 INNER JOIN account_tax t ON (r.account_tax_id = t.id)
                 WHERE %s GROUP BY r.account_tax_id"""
        return sql

    # ---------- Compute Tax and Net ----------
    def _compute_from_amls(self, options, taxes):
        # compute the tax amount
        sql = self._sql_from_amls_one()
        tables, where_clause, where_params = self.env['account.move.line']._query_get()
        query = sql % (tables, where_clause)
        self.env.cr.execute(query, where_params)
        results = self.env.cr.fetchall()
        for result in results:
            if result[0] in taxes:
                taxes[result[0]]['tax'] = abs(result[1])

        # compute the net amount
        sql2 = self._sql_from_amls_two()
        query = sql2 % (tables, where_clause)
        self.env.cr.execute(query, where_params)
        results = self.env.cr.fetchall()
        for result in results:
            if result[0] in taxes:
                taxes[result[0]]['net'] = abs(result[1])

    # ---------- Get Transactions for a Tax ----------
    @api.model
    def get_transactions_for_tax(self, tax, options):
        domain = [
            ('tax_ids', 'in', tax.ids),
            ('move_id.state', '=', 'posted'),
            ('move_id.date', '>=', options['date_from']),
            ('move_id.date', '<=', options['date_to']),
        ]
        lines = self.env['account.move.line'].search(domain)

        transactions = []
        for line in lines:
            transactions.append({
                'invoice': line.move_id.name,
                'date': line.move_id.date,
                'partner': line.move_id.partner_id.name,
                'base': abs(line.debit - line.credit),
                'tax': abs(sum(t.amount for t in line.tax_ids)),
            })
        return transactions

    # ---------- Build Lines ----------
    @api.model
    def get_lines(self, options):
        taxes = {}
        # collect all taxes
        for tax in self.env['account.tax'].search([('type_tax_use', '!=', 'none')]):
            if tax.children_tax_ids:
                for child in tax.children_tax_ids:
                    if child.type_tax_use != 'none':
                        continue
                    taxes[child.id] = {'tax': 0, 'net': 0, 'name': child.name, 'type': tax.type_tax_use}
            else:
                taxes[tax.id] = {'tax': 0, 'net': 0, 'name': tax.name, 'type': tax.type_tax_use}

        # compute totals
        self.with_context(
            date_from=options['date_from'],
            date_to=options['date_to'],
            state=options['target_move'],
            strict_range=True
        )._compute_from_amls(options, taxes)

        # separate sale and purchase groups
        groups = {'sale': [], 'purchase': []}
        for tax_id, tax in taxes.items():
            if tax['tax'] or tax['net']:
                # attach transactions for detailed view
                tax_record = self.env['account.tax'].browse(tax_id)
                tax['transactions'] = self.get_transactions_for_tax(tax_record, options)
                groups[tax['type']].append(tax)

        return groups

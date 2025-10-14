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
        if not data or not data.get('form'):
            raise UserError(_("Form content is missing, this report cannot be printed."))

        options = data['form']

        # ------------------ CLICKABLE TAX DETAIL ------------------
        tax_id = self.env.context.get('tax_id')
        date_from = self.env.context.get('date_from')
        date_to = self.env.context.get('date_to')
        if tax_id:
            lines = self.get_lines_for_tax(tax_id, date_from, date_to)
            return {
                'data': options,
                'lines': lines,
                'report_type': 'detailed',
            }
        # -----------------------------------------------------------

        # Normal/detailed report for all taxes
        lines = self.get_lines(options)
        report_type = 'detailed' if options.get('detailed_summary') else 'normal'

        return {
            'data': options,
            'lines': lines,
            'report_type': report_type,
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
        # Compute tax amount
        sql = self._sql_from_amls_one()
        tables, where_clause, where_params = self.env['account.move.line']._query_get()
        query = sql % (tables, where_clause)
        self.env.cr.execute(query, where_params)
        results = self.env.cr.fetchall()
        for result in results:
            if result[0] in taxes:
                taxes[result[0]]['tax'] = abs(result[1])

        # Compute net amount
        sql2 = self._sql_from_amls_two()
        query = sql2 % (tables, where_clause)
        self.env.cr.execute(query, where_params)
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
                    taxes[child.id] = {'tax': 0, 'net': 0, 'name': child.name, 'type': tax.type_tax_use, 'transactions': []}
            else:
                taxes[tax.id] = {'tax': 0, 'net': 0, 'name': tax.name, 'type': tax.type_tax_use, 'transactions': []}

        self.with_context(
            date_from=options['date_from'],
            date_to=options['date_to'],
            state=options['target_move'],
            strict_range=True
        )._compute_from_amls(options, taxes)

        groups = dict((tp, []) for tp in ['sale', 'purchase'])
        for tax_id, tax_data in taxes.items():
            if tax_data['tax'] or tax_data['net']:
                # Collect transactions for detailed view
                transactions = []
                for move in self.env['account.move'].search([
                    ('date', '>=', options['date_from']),
                    ('date', '<=', options['date_to']),
                    ('state', '=', 'posted' if options['target_move'] == 'posted' else 'draft')
                ]):
                    for line in move.line_ids.filtered(lambda l: l.tax_line_id.id == tax_id):
                        transactions.append({
                            'invoice': move.name,
                            'date': move.date,
                            'partner': move.partner_id.name,
                            'base': abs(line.balance - line.tax_amount if hasattr(line, 'tax_amount') else line.debit - line.credit),
                            'tax': abs(line.balance),
                        })
                tax_data['transactions'] = transactions
                groups[tax_data['type']].append(tax_data)
        return groups

    @api.model
    def get_lines_for_tax(self, tax_id, date_from, date_to):
        """Return detailed transactions for a specific tax"""
        taxes = {tax_id: {'tax': 0, 'net': 0, 'name': self.env['account.tax'].browse(tax_id).name,
                          'type': self.env['account.tax'].browse(tax_id).type_tax_use, 'transactions': []}}
        self.with_context(
            date_from=date_from,
            date_to=date_to,
            state='posted',
            strict_range=True
        )._compute_from_amls({}, taxes)

        # Collect transactions
        tax_data = taxes[tax_id]
        transactions = []
        for move in self.env['account.move'].search([
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('state', '=', 'posted')
        ]):
            for line in move.line_ids.filtered(lambda l: l.tax_line_id.id == tax_id):
                transactions.append({
                    'invoice': move.name,
                    'date': move.date,
                    'partner': move.partner_id.name,
                    'base': abs(line.balance - line.tax_amount if hasattr(line, 'tax_amount') else line.debit - line.credit),
                    'tax': abs(line.balance),
                })
        tax_data['transactions'] = transactions
        return {'sale' if tax_data['type'] == 'sale' else 'purchase': [tax_data]}

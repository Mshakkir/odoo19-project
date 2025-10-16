# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class AccountingReportInherit(models.TransientModel):
    _inherit = 'accounting.report'  # Inherit the Odoomates balance sheet wizard

    def action_show_details(self):
        """
        Build domain from wizard options, aggregate account_move_line by account,
        create balance.sheet.line transient records, and open tree view.
        """
        self.ensure_one()

        # Collect filters for domain
        aml_domain = [('company_id', '=', self.env.company.id)]
        if self.date_from:
            aml_domain.append(('date', '>=', self.date_from))
        if self.date_to:
            aml_domain.append(('date', '<=', self.date_to))
        if getattr(self, 'target_move', False) and self.target_move == 'posted':
            aml_domain.append(('move_id.state', '=', 'posted'))
        if getattr(self, 'journal_ids', False) and self.journal_ids:
            aml_domain.append(('journal_id', 'in', self.journal_ids.ids))

        # SQL query to aggregate debit/credit by account
        query = """
            SELECT 
                aml.account_id AS account_id,
                SUM(aml.debit) AS total_debit,
                SUM(aml.credit) AS total_credit
            FROM account_move_line AS aml
            JOIN account_move AS am ON aml.move_id = am.id
            WHERE aml.company_id = %s
        """
        params = [self.env.company.id]
        where_clauses = []

        for clause in aml_domain:
            field, op, val = clause
            if field.startswith('move_id.'):
                field = field.replace('move_id.', 'am.')
            else:
                field = f"aml.{field}"

            if op == 'in':
                if not val:
                    where_clauses.append("FALSE")
                else:
                    where_clauses.append(f"{field} IN %s")
                    params.append(tuple(val))
            else:
                where_clauses.append(f"{field} {op} %s")
                params.append(val)

        if where_clauses:
            query += " AND " + " AND ".join(where_clauses)

        query += " GROUP BY aml.account_id ORDER BY aml.account_id"

        _logger.info("Running Balance Sheet query: %s with params %s", query, params)

        self.env.cr.execute(query, tuple(params))
        rows = self.env.cr.dictfetchall()

        # Clear previous temporary records
        existing_lines = self.env['balance.sheet.line'].search([('wizard_id', '=', self.id)])
        if existing_lines:
            existing_lines.unlink()

        BalanceLine = self.env['balance.sheet.line']
        for row in rows:
            BalanceLine.create({
                'wizard_id': self.id,
                'account_id': row.get('account_id'),
                'debit': row.get('total_debit') or 0.0,
                'credit': row.get('total_credit') or 0.0,
            })

        # Return proper action
        return {
            'name': _('Balance Sheet Details'),
            'type': 'ir.actions.act_window',
            'res_model': 'balance.sheet.line',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [('wizard_id', '=', self.id)],
            'context': {'default_wizard_id': self.id},
        }







# # -*- coding: utf-8 -*-
# from odoo import api, fields, models, _
# from odoo.exceptions import UserError
# import logging
#
# _logger = logging.getLogger(__name__)
#
#
# class AccountingReportInherit(models.TransientModel):
#     _inherit = 'accounting.report'  # Inherit the Odoomates balance sheet wizard
#
#     def action_show_details(self):
#         """
#         Build domain from wizard options, aggregate account_move_line by account,
#         create balance.sheet.line transient records, and open tree view.
#         """
#         self.ensure_one()
#
#         # Collect filters
#         aml_domain = []
#         if self.date_from:
#             aml_domain.append(('date', '>=', self.date_from))
#         if self.date_to:
#             aml_domain.append(('date', '<=', self.date_to))
#         if hasattr(self, 'target_move') and self.target_move == 'posted':
#             aml_domain.append(('move_id.state', '=', 'posted'))
#         if self.journal_ids:
#             aml_domain.append(('journal_id', 'in', self.journal_ids.ids))
#
#         # Start SQL query with JOIN to account_move
#         query = """
#             SELECT
#                 aml.account_id AS account_id,
#                 SUM(aml.debit) AS total_debit,
#                 SUM(aml.credit) AS total_credit
#             FROM account_move_line AS aml
#             JOIN account_move AS am ON aml.move_id = am.id
#             WHERE TRUE
#         """
#         params = []
#         where_clauses = []
#
#         # Dynamically add WHERE conditions
#         for clause in aml_domain:
#             field, op, val = clause
#             # Prefix table aliases properly
#             if field.startswith('move_id.'):
#                 field = field.replace('move_id.', 'am.')
#             else:
#                 field = f"aml.{field}"
#
#             if op == 'in':
#                 if not val:
#                     where_clauses.append("FALSE")  # Avoid empty IN ()
#                 else:
#                     where_clauses.append(f"{field} IN %s")
#                     params.append(tuple(val))
#             else:
#                 where_clauses.append(f"{field} {op} %s")
#                 params.append(val)
#
#         if where_clauses:
#             query += " AND " + " AND ".join(where_clauses)
#
#         query += " GROUP BY aml.account_id ORDER BY aml.account_id"
#
#         _logger.info("Running Balance Sheet query: %s with params %s", query, params)
#
#         # Execute query safely
#         self.env.cr.execute(query, tuple(params))
#         rows = self.env.cr.dictfetchall()
#
#         # Remove old temporary records
#         existing_lines = self.env['balance.sheet.line'].search([('wizard_id', '=', self.id)])
#         if existing_lines:
#             existing_lines.unlink()
#
#         # Create new balance sheet lines
#         BalanceLine = self.env['balance.sheet.line']
#         for row in rows:
#             BalanceLine.create({
#                 'wizard_id': self.id,
#                 'account_id': row.get('account_id'),
#                 'debit': row.get('total_debit') or 0.0,
#                 'credit': row.get('total_credit') or 0.0,
#             })
#
#         # Return a tree view action to show results
#         return {
#             'name': _('Balance Sheet Details'),
#             'type': 'ir.actions.act_window',
#             'res_model': 'balance.sheet.line',
#             'view_mode': 'list,form',
#             'target': 'current',
#             'domain': [('wizard_id', '=', self.id)],
#             'context': {'default_wizard_id': self.id},
#         }

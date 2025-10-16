# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class AccountingReportInherit(models.TransientModel):
    _inherit = 'accounting.report'   # inherit the odoomates wizard model

    def action_show_details(self):
        """
        Build domain from wizard options, aggregate account_move_line by account,
        create balance.sheet.line transient records and open tree view.
        """
        self.ensure_one()

        # Build base domain on account.move.line
        aml_domain = []
        # Dates
        if self.date_from:
            aml_domain.append(('date', '>=', self.date_from))
        if self.date_to:
            aml_domain.append(('date', '<=', self.date_to))
        # Target moves (posted vs all)
        if hasattr(self, 'target_move') and self.target_move == 'posted':
            # move.state = 'posted'
            aml_domain.append(('move_id.state', '=', 'posted'))
        # Journals
        if self.journal_ids:
            aml_domain.append(('journal_id', 'in', self.journal_ids.ids))

        # Optionally filter account_report selection (if default_account_report_id is set)
        # We'll not try to parse account.financial.report relationships; instead select accounts
        # that have move lines in the date/journal filters — this is generic and safe.

        # SQL aggregation for efficiency
        query = """
            SELECT account_id, SUM(debit) as total_debit, SUM(credit) as total_credit
            FROM account_move_line
            WHERE TRUE
        """
        params = []
        # append conditions corresponding to aml_domain
        where_clauses = []
        for clause in aml_domain:
            field, op, val = clause
            # convert tuple conditions
            if op == 'in':
                # ensure tuple
                if not val:
                    where_clauses.append("FALSE")  # empty list — no results
                else:
                    where_clauses.append("%s IN %s" % (field, '%s'))
                    params.append(tuple(val))
            else:
                where_clauses.append("%s %s %s" % (field, op, '%s'))
                params.append(val)
        if where_clauses:
            query += " AND " + " AND ".join(where_clauses)
        query += " GROUP BY account_id ORDER BY account_id"

        # Execute query
        self.env.cr.execute(query, tuple(params))
        rows = self.env.cr.dictfetchall()

        # Remove old transient lines for this wizard (if any)
        existing = self.env['balance.sheet.line'].search([('wizard_id', '=', self.id)])
        if existing:
            existing.unlink()

        # Create transient lines for each account
        for row in rows:
            account_id = row.get('account_id')
            debit = row.get('total_debit') or 0.0
            credit = row.get('total_credit') or 0.0
            self.env['balance.sheet.line'].create({
                'wizard_id': self.id,
                'account_id': account_id,
                'debit': debit,
                'credit': credit,
            })

        # Return action to open our transient tree
        return {
            'name': _('Balance Sheet Details'),
            'type': 'ir.actions.act_window',
            'res_model': 'balance.sheet.line',
            'view_mode': 'tree,form',
            'target': 'current',
            'domain': [('wizard_id', '=', self.id)],
            'context': {
                # keep original wizard context for ease of navigation
                'default_wizard_id': self.id,
            }
        }

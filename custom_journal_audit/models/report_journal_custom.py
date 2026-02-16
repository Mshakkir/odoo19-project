# -*- coding: utf-8 -*-
from odoo import api, models, _
from odoo.exceptions import UserError


class ReportJournalCustom(models.AbstractModel):
    """
    Custom Journal Audit Report with entry number filtering
    """
    _inherit = 'report.accounting_pdf_reports.report_journal'

    def lines(self, target_move, journal_ids, sort_selection, data):
        """Override to add journal entry number filtering"""
        if isinstance(journal_ids, int):
            journal_ids = [journal_ids]

        move_state = ['draft', 'posted']
        if target_move == 'posted':
            move_state = ['posted']

        query_get_clause = self._get_query_get_clause(data)
        params = [tuple(move_state), tuple(journal_ids)] + query_get_clause[2]

        # Base query
        query = '''
            SELECT "account_move_line".id 
            FROM ''' + query_get_clause[0] + ''', account_move am, account_account acc 
            WHERE "account_move_line".account_id = acc.id 
            AND "account_move_line".move_id=am.id 
            AND am.state IN %s 
            AND "account_move_line".journal_id IN %s 
            AND ''' + query_get_clause[1]

        # Add journal entry number filtering if provided
        entry_number_from = data.get('form', {}).get('entry_number_from')
        entry_number_to = data.get('form', {}).get('entry_number_to')

        if entry_number_from:
            query += ' AND am.name >= %s'
            params.append(entry_number_from)

        if entry_number_to:
            query += ' AND am.name <= %s'
            params.append(entry_number_to)

        # Add sorting
        query += ' ORDER BY '
        if sort_selection == 'date':
            query += '"account_move_line".date'
        else:
            query += 'am.name'
        query += ', "account_move_line".move_id'

        self.env.cr.execute(query, tuple(params))
        ids = (x[0] for x in self.env.cr.fetchall())
        return self.env['account.move.line'].browse(ids)

    @api.model
    def _get_report_values(self, docids, data=None):
        """Override to pass custom filters to the report"""
        if not data.get('form'):
            raise UserError(_("Form content is missing, this report cannot be printed."))

        # Get values from parent
        result = super(ReportJournalCustom, self)._get_report_values(docids, data)

        # Add custom data
        result.update({
            'show_details': data['form'].get('show_details', False),
            'entry_number_from': data['form'].get('entry_number_from', ''),
            'entry_number_to': data['form'].get('entry_number_to', ''),
        })

        return result
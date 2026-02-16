from odoo import fields, models, api, _
from odoo.exceptions import UserError


class AccountPrintJournalDetails(models.TransientModel):
    _inherit = "account.print.journal"

    def check_report_details(self):
        """Open detailed view of journal entries based on wizard filters"""
        self.ensure_one()

        # Build base domain
        domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ]

        # Add journal filter
        if self.journal_ids:
            domain.append(('journal_id', 'in', self.journal_ids.ids))

        # Add target move filter
        if self.target_move == 'posted':
            domain.append(('parent_state', '=', 'posted'))

        # Add company filter if multi-company
        if self.company_id:
            domain.append(('company_id', '=', self.company_id.id))

        # Get move lines
        move_lines = self.env['account.move.line'].search(domain)

        # Apply display account filter if needed
        if not move_lines:
            # Build helpful error message
            error_msg = _('No journal entries found for the selected criteria.\n\nPlease check:')
            error_details = []
            error_details.append(f'- Date range: {self.date_from} to {self.date_to}')
            if self.journal_ids:
                error_details.append(f'- Journals: {", ".join(self.journal_ids.mapped("name"))}')
            error_details.append(f'- Target Moves: {self.target_move}')

            raise UserError(error_msg + '\n' + '\n'.join(error_details))

        # Build context for proper grouping
        context = {
            'search_default_group_by_journal': 1,
        }

        # Build a descriptive name
        title = _('Journal Audit Details')
        title_parts = []

        if self.journal_ids:
            if len(self.journal_ids) == 1:
                title_parts.append(self.journal_ids[0].name)
            else:
                title_parts.append(f'{len(self.journal_ids)} Journals')

        if self.target_move == 'posted':
            title_parts.append('Posted Only')

        if title_parts:
            title += ' - ' + ' | '.join(title_parts)

        # Determine sort order
        if self.sort_selection == 'date':
            context['search_default_sort_date'] = 1
        else:
            context['search_default_sort_move'] = 1

        return {
            'name': title,
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'list',
            'view_id': self.env.ref('journal_audit_details.view_journal_audit_line_tree').id,
            'domain': [('id', 'in', move_lines.ids)],
            'context': context,
            'target': 'current',
        }
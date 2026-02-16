from odoo import fields, models, api, _
from odoo.exceptions import UserError


class AccountPrintJournalDetails(models.TransientModel):
    _inherit = "account.print.journal"

    # Override to remove required=True and clear the default
    # so users can leave it empty to mean "all journals"
    journal_ids = fields.Many2many(
        'account.journal',
        string='Journals',
        required=False,
        default=lambda self: self.env['account.journal'].browse()
    )

    def check_report_details(self):
        """Open detailed view of journal entries based on wizard filters"""
        self.ensure_one()

        domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ]

        # If journals are selected, filter by them; otherwise include all
        if self.journal_ids:
            domain.append(('journal_id', 'in', self.journal_ids.ids))

        if self.target_move == 'posted':
            domain.append(('parent_state', '=', 'posted'))

        if self.company_id:
            domain.append(('company_id', '=', self.company_id.id))

        move_lines = self.env['account.move.line'].search(domain)

        if not move_lines:
            error_msg = _('No journal entries found for the selected criteria.\n\nPlease check:')
            error_details = [f'- Date range: {self.date_from} to {self.date_to}']
            if self.journal_ids:
                error_details.append(f'- Journals: {", ".join(self.journal_ids.mapped("name"))}')
            else:
                error_details.append('- Journals: All')
            error_details.append(f'- Target Moves: {self.target_move}')
            raise UserError(error_msg + '\n' + '\n'.join(error_details))

        # Build title
        title = _('Journal Audit Details')
        title_parts = []
        if self.journal_ids:
            if len(self.journal_ids) == 1:
                title_parts.append(self.journal_ids[0].name)
            else:
                title_parts.append(f'{len(self.journal_ids)} Journals')
        else:
            title_parts.append('All Journals')

        if self.target_move == 'posted':
            title_parts.append('Posted Only')

        if title_parts:
            title += ' - ' + ' | '.join(title_parts)

        return {
            'name': title,
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'list',
            'view_id': self.env.ref('journal_audit_details.view_journal_audit_line_tree').id,
            'domain': [('id', 'in', move_lines.ids)],
            'context': {'group_by': 'journal_id'},
            'target': 'current',
        }
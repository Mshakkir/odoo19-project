import logging
from odoo import fields, models, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountPrintJournalDetails(models.TransientModel):
    _inherit = "account.print.journal"

    # Override field: not required, empty default
    journal_ids = fields.Many2many(
        'account.journal',
        string='Journals',
        required=False,
        default=False,
    )

    # ── New field: Journal Entry Number filter ────────────────────────────────
    # Shown only when sort_selection == 'move_name'
    # User types e.g. INV/2026/00001 to filter results to that specific entry
    journal_entry_number = fields.Char(
        string='Journal Entry Number',
        help='Enter a specific journal entry number to filter results (e.g. INV/2026/00001). '
             'Leave empty to include all entries.',
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        res['journal_ids'] = [(6, 0, [])]
        return res

    @api.onchange('date_from', 'date_to', 'company_id')
    def _onchange_clear_journal_ids(self):
        """Block parent onchange from repopulating journal_ids."""
        self.journal_ids = [(5, 0, 0)]

    @api.onchange('sort_selection')
    def _onchange_sort_selection(self):
        """Clear journal entry number when switching sort mode."""
        if self.sort_selection != 'move_name':
            self.journal_entry_number = False

    def check_report_details(self):
        """Open detailed view of journal entries based on wizard filters"""
        self.ensure_one()

        # ── Validate dates ────────────────────────────────────────────────────
        if not self.date_from or not self.date_to:
            raise UserError(_('Please set both Start Date and End Date before clicking Show Details.'))

        if self.date_from > self.date_to:
            raise UserError(_('Start Date cannot be after End Date.'))

        # ── Build domain ──────────────────────────────────────────────────────
        domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ]

        if self.journal_ids:
            domain.append(('journal_id', 'in', self.journal_ids.ids))

        if self.target_move == 'posted':
            domain.append(('parent_state', '=', 'posted'))

        if self.company_id:
            domain.append(('company_id', '=', self.company_id.id))

        # ── Journal Entry Number filter ───────────────────────────────────────
        # If user selected "Journal Entry Number" mode AND typed a number,
        # filter results to only lines belonging to that specific entry
        if self.sort_selection == 'move_name' and self.journal_entry_number:
            entry_number = self.journal_entry_number.strip()
            # Search with ilike so partial matches work too
            # e.g. typing "INV/2026" will match all invoices in 2026
            domain.append(('move_name', 'ilike', entry_number))

        # ── Search ────────────────────────────────────────────────────────────
        move_lines = self.env['account.move.line'].search(domain, order='move_name asc, date asc')

        if not move_lines:
            error_msg = _('No journal entries found for the selected criteria.\n\nPlease check:')
            error_details = [f'- Date range: {self.date_from} to {self.date_to}']
            if self.journal_ids:
                error_details.append(f'- Journals: {", ".join(self.journal_ids.mapped("name"))}')
            else:
                error_details.append('- Journals: All')
            if self.sort_selection == 'move_name' and self.journal_entry_number:
                error_details.append(f'- Journal Entry No.: {self.journal_entry_number}')
            error_details.append(f'- Target Moves: {self.target_move}')
            raise UserError(error_msg + '\n' + '\n'.join(error_details))

        # ── Build title ───────────────────────────────────────────────────────
        title = _('Journal Audit Details')
        title_parts = []

        if self.journal_ids:
            title_parts.append(
                self.journal_ids[0].name if len(self.journal_ids) == 1
                else f'{len(self.journal_ids)} Journals'
            )
        else:
            title_parts.append('All Journals')

        if self.sort_selection == 'move_name' and self.journal_entry_number:
            title_parts.append(f'Entry: {self.journal_entry_number.strip()}')

        if self.target_move == 'posted':
            title_parts.append('Posted Only')

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
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

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        res['journal_ids'] = [(6, 0, [])]
        return res

    @api.onchange('date_from', 'date_to', 'company_id')
    def _onchange_clear_journal_ids(self):
        """Block parent onchange from repopulating journal_ids."""
        self.journal_ids = [(5, 0, 0)]

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

        # ── Apply sort_selection ──────────────────────────────────────────────
        # sort_selection values from Odoo Mates:
        #   'date'      → sort by date, then journal entry number
        #   'move_name' → sort by journal entry number only
        if self.sort_selection == 'date':
            order = 'date asc, move_name asc'
        else:
            # 'move_name' = Journal Entry Number (default)
            order = 'move_name asc'

        # ── Search ────────────────────────────────────────────────────────────
        move_lines = self.env['account.move.line'].search(domain, order=order)

        if not move_lines:
            error_msg = _('No journal entries found for the selected criteria.\n\nPlease check:')
            error_details = [f'- Date range: {self.date_from} to {self.date_to}']
            if self.journal_ids:
                error_details.append(f'- Journals: {", ".join(self.journal_ids.mapped("name"))}')
            else:
                error_details.append('- Journals: All')
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

        if self.target_move == 'posted':
            title_parts.append('Posted Only')

        sort_label = 'Sorted by Date' if self.sort_selection == 'date' else 'Sorted by Entry No.'
        title_parts.append(sort_label)

        title += ' - ' + ' | '.join(title_parts)

        # ── Pass order to context so list view respects it ────────────────────
        context = {
            'group_by': 'journal_id',
            'order': order,
        }

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
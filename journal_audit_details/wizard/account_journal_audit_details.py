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
        # Force empty — parent's default_get already returns empty
        # due to our field override, but being explicit is safer
        res['journal_ids'] = [(6, 0, [])]
        return res

    # ── KEY FIX ──────────────────────────────────────────────────────────────
    # The onchange on date_from / date_to / company_id in the parent model
    # (account.common.journal.report or account.print.journal) is re-populating
    # journal_ids AFTER default_get returns empty.
    #
    # We override every possible onchange that touches journal_ids and make
    # sure journal_ids stays at whatever the user has set (including empty).
    # ─────────────────────────────────────────────────────────────────────────

    @api.onchange('date_from', 'date_to', 'company_id')
    def _onchange_clear_journal_ids(self):
        """
        The parent's onchange repopulates journal_ids when dates/company change.
        We intercept it and keep journal_ids empty (user controls it manually).
        """
        _logger.warning("=== JOURNAL AUDIT DEBUG: _onchange_clear_journal_ids triggered ===")
        _logger.warning("journal_ids before clear: %s", self.journal_ids)

        # Only clear if the user hasn't manually selected journals yet.
        # Since we want the field to start empty and stay empty unless
        # the user explicitly picks journals, we always set it to empty here.
        self.journal_ids = [(5, 0, 0)]  # Command 5 = clear all

        _logger.warning("journal_ids after clear: %s", self.journal_ids)

    def check_report_details(self):
        """Open detailed view of journal entries based on wizard filters"""
        self.ensure_one()

        _logger.warning("=== check_report_details: journal_ids = %s", self.journal_ids)

        domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ]

        if self.journal_ids:
            domain.append(('journal_id', 'in', self.journal_ids.ids))
        else:
            _logger.warning("No journals selected — fetching ALL journals")

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
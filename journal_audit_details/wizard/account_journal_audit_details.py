import logging
from odoo import fields, models, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountPrintJournalDetails(models.TransientModel):
    _inherit = "account.print.journal"

    # Override to clear default and remove required
    journal_ids = fields.Many2many(
        'account.journal',
        string='Journals',
        required=False,
        default=False,
    )

    @api.model
    def default_get(self, fields_list):
        """
        DEBUG: Override default_get to log what defaults are being set
        and force journal_ids to be empty.
        """
        _logger.warning("=== JOURNAL AUDIT DEBUG: default_get called ===")
        _logger.warning("Fields requested: %s", fields_list)

        # Call super to get all defaults
        res = super().default_get(fields_list)

        _logger.warning("=== Defaults BEFORE our override: %s ===", res)

        # Force journal_ids empty regardless of what parent set
        # Many2many uses ORM command (6, 0, [ids]) — empty list clears all
        res['journal_ids'] = [(6, 0, [])]

        _logger.warning("=== Defaults AFTER our override: %s ===", res)
        return res

    def check_report_details(self):
        """Open detailed view of journal entries based on wizard filters"""
        self.ensure_one()

        _logger.warning("=== JOURNAL AUDIT DEBUG: check_report_details called ===")
        _logger.warning("journal_ids: %s", self.journal_ids)
        _logger.warning("date_from: %s | date_to: %s", self.date_from, self.date_to)
        _logger.warning("target_move: %s", self.target_move)

        domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ]

        if self.journal_ids:
            domain.append(('journal_id', 'in', self.journal_ids.ids))
            _logger.warning("Filtering by journals: %s", self.journal_ids.mapped('name'))
        else:
            _logger.warning("No journals selected — fetching ALL journals")

        if self.target_move == 'posted':
            domain.append(('parent_state', '=', 'posted'))

        if self.company_id:
            domain.append(('company_id', '=', self.company_id.id))

        _logger.warning("Final domain: %s", domain)

        move_lines = self.env['account.move.line'].search(domain)

        _logger.warning("Move lines found: %s", len(move_lines))

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
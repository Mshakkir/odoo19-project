# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class AccountPrintJournalCustom(models.TransientModel):
    """
    Custom Journal Audit - Inherits from OdooMates account.print.journal
    """
    _inherit = "account.print.journal"

    # Override journal_ids to remove default selection
    journal_ids = fields.Many2many(
        'account.journal',
        string='Journals',
        required=True,
        default=lambda self: self.env['account.journal'],  # Empty recordset
        help="Select the journals you want to audit"
    )

    # Add journal entry number filter
    entry_number_from = fields.Char(
        string='Entry Number From',
        help="Filter entries starting from this journal entry number"
    )

    entry_number_to = fields.Char(
        string='Entry Number To',
        help="Filter entries up to this journal entry number"
    )

    # Add show details functionality
    show_details = fields.Boolean(
        string='Show Details',
        default=False,
        help="Show detailed information in the report"
    )

    @api.model
    def default_get(self, fields_list):
        """Override default_get to ensure journals are not auto-selected"""
        res = super(AccountPrintJournalCustom, self).default_get(fields_list)
        # Explicitly set journal_ids to empty if it was populated by parent
        if 'journal_ids' in res and res.get('journal_ids'):
            res['journal_ids'] = []
        return res

    def _get_report_data(self, data):
        """Override to add custom filters"""
        data = super(AccountPrintJournalCustom, self)._get_report_data(data)
        data['form'].update({
            'entry_number_from': self.entry_number_from,
            'entry_number_to': self.entry_number_to,
            'show_details': self.show_details,
        })
        return data

    def action_show_details(self):
        """
        Show details button action - displays the report with detailed view
        """
        self.ensure_one()

        # Validate that journals are selected
        if not self.journal_ids:
            raise UserError(_('Please select at least one journal.'))

        # Set show_details to True
        self.show_details = True

        # Prepare data for the report - Include ALL fields needed by parent methods
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')

        # Read all required fields including company_id
        read_fields = [
            'date_from', 'date_to', 'journal_ids', 'target_move',
            'sort_selection', 'amount_currency', 'entry_number_from',
            'entry_number_to', 'show_details', 'company_id'
        ]
        data['form'] = self.read(read_fields)[0]

        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context, lang=self.env.context.get('lang') or 'en_US')

        # Return the report action
        return self.env.ref('accounting_pdf_reports.action_report_journal').with_context(landscape=True).report_action(
            self, data=data)

    def _print_report(self, data):
        """Override print report to validate journal selection"""
        if not self.journal_ids:
            raise UserError(_('Please select at least one journal before printing.'))

        return super(AccountPrintJournalCustom, self)._print_report(data)
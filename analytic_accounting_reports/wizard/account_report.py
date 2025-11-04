# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountingReport(models.TransientModel):
    _inherit = "accounting.report"

    # Analytic filter fields
    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        string="",
        help=(
            "Select specific warehouses/analytic accounts for filtering.\n"
            "• Leave empty: Show all warehouses combined\n"
            "• Select ONE: Show only that warehouse (separate report)\n"
            "• Select MULTIPLE: Show combined with optional breakdown"
        )
    )

    include_combined = fields.Boolean(
        string='Show Combined Column',
        default=False,
        help='Show a combined total column when multiple analytic accounts are selected.'
    )

    warehouse_selection_info = fields.Html(
        string='Selection Info',
        compute='_compute_warehouse_info',
        store=False
    )

    # -----------------------------
    # Computed fields
    # -----------------------------
    @api.depends('analytic_account_ids')
    def _compute_warehouse_info(self):
        """Show helpful info about what report will be generated"""
        for record in self:
            count = len(record.analytic_account_ids)
            if count == 0:
                info = '<span style="color:#0066cc;">📊 Will show <b>ALL WAREHOUSES COMBINED</b></span>'
            elif count == 1:
                name = record.analytic_account_ids[0].name
                info = f'<span style="color:#28a745;">📋 Will show <b>{name} ONLY</b> (Separate Report)</span>'
            else:
                info = (
                    f'<span style="color:#ff6600;">📦 Will show <b>{count} WAREHOUSES COMBINED</b> '
                    f'(with optional breakdown)</span>'
                )
            record.warehouse_selection_info = info

    # -----------------------------
    # Onchange methods
    # -----------------------------
    @api.onchange('analytic_account_ids')
    def _onchange_analytic_account_ids(self):
        """Auto-disable combined column when only one analytic is selected"""
        if len(self.analytic_account_ids) <= 1:
            self.include_combined = False

    # -----------------------------
    # Context builders
    # -----------------------------
    def _build_contexts(self, data):
        """Override to add analytic account context"""
        result = super()._build_contexts(data)

        analytic_ids = []
        form_data = data.get('form', {})
        analytic_data = form_data.get('analytic_account_ids', [])

        # Handle different formats of many2many field
        if analytic_data:
            if isinstance(analytic_data, (list, tuple)) and analytic_data:
                if isinstance(analytic_data[0], (list, tuple)):
                    # Format: [(6, 0, [ids])]
                    analytic_ids = analytic_data[0][2] if len(analytic_data[0]) > 2 else []
                else:
                    # Format: [id1, id2, ...]
                    analytic_ids = list(analytic_data)

        result['analytic_account_ids'] = analytic_ids
        result['include_combined'] = form_data.get('include_combined', False)
        return result

    def _build_comparison_context(self, data):
        """Override to add analytic account context for comparison"""
        result = super()._build_comparison_context(data)

        analytic_ids = []
        form_data = data.get('form', {})
        analytic_data = form_data.get('analytic_account_ids', [])

        if analytic_data:
            if isinstance(analytic_data, (list, tuple)) and analytic_data:
                if isinstance(analytic_data[0], (list, tuple)):
                    analytic_ids = analytic_data[0][2] if len(analytic_data[0]) > 2 else []
                else:
                    analytic_ids = list(analytic_data)

        result['analytic_account_ids'] = analytic_ids
        result['include_combined'] = form_data.get('include_combined', False)
        return result

    # -----------------------------
    # Main report action
    # -----------------------------
    def check_report(self):
        """Override to inject analytic data into the report"""
        self.ensure_one()

        parent_fields = [
            'date_from_cmp', 'debit_credit', 'date_to_cmp',
            'filter_cmp', 'account_report_id', 'enable_filter',
            'label_filter', 'target_move', 'date_from', 'date_to',
            'journal_ids', 'company_id'
        ]

        all_fields = parent_fields + ['analytic_account_ids', 'include_combined']

        data = {
            'ids': self.env.context.get('active_ids', []),
            'model': self.env.context.get('active_model', 'ir.ui.menu'),
        }

        form_data = self.read(all_fields)[0]
        data['form'] = form_data

        # Ensure analytic_account_ids is in proper format
        if self.analytic_account_ids:
            data['form']['analytic_account_ids'] = [(6, 0, self.analytic_account_ids.ids)]
        else:
            data['form']['analytic_account_ids'] = []

        data['form']['include_combined'] = self.include_combined

        # Clean tuple date fields
        for field in ['date_from_cmp', 'date_to_cmp', 'date_from', 'date_to']:
            if field in data['form'] and data['form'][field]:
                if isinstance(data['form'][field], tuple):
                    data['form'][field] = data['form'][field][0]

        used_context = self._build_contexts(data)
        data['form']['used_context'] = used_context
        comparison_context = self._build_comparison_context(data)
        data['form']['comparison_context'] = comparison_context

        return self.env.ref('accounting_pdf_reports.action_report_financial').with_context(
            **used_context
        ).report_action(self, data=data, config=False)

    # -----------------------------
    # New Button Action (Fix for XML)
    # -----------------------------
    def action_view_details(self):
        """Dummy 'View Details' action to fix XML button call.
        You can later replace this with your own logic.
        """
        return {
            'type': 'ir.actions.act_window',
            'name': 'Accounting Details',
            'res_model': 'account.move.line',
            'view_mode': 'tree,form',
            'target': 'current',
            'domain': [],  # You can filter results based on analytic_account_ids if needed
        }















# # -*- coding: utf-8 -*-
# from odoo import api, fields, models
#
#
# class AccountingReport(models.TransientModel):
#     _inherit = "accounting.report"
#
#     # Analytic filter fields
#     analytic_account_ids = fields.Many2many(
#         'account.analytic.account',
#         string="",
#         help="Select specific warehouses/analytic accounts for filtering.\n"
#              "• Leave empty: Show all warehouses combined\n"
#              "• Select ONE: Show only that warehouse (separate report)\n"
#              "• Select MULTIPLE: Show combined with optional breakdown"
#     )
#
#     include_combined = fields.Boolean(
#         string='Show Combined Column',
#         default=False,
#         help='Show a combined total column when multiple analytic accounts are selected.'
#     )
#     warehouse_selection_info = fields.Html(
#         string='Selection Info',
#         compute='_compute_warehouse_info',
#         store=False
#     )
#
#     @api.depends('analytic_account_ids')
#     def _compute_show_breakdown(self):
#         """Compute whether to show warehouse breakdown"""
#         for record in self:
#             record.show_warehouse_breakdown = len(record.analytic_account_ids) > 1
#
#     @api.depends('analytic_account_ids')
#     def _compute_warehouse_info(self):
#         """Show helpful info about what report will be generated"""
#         for record in self:
#             count = len(record.analytic_account_ids)
#             if count == 0:
#                 info = '<span style="color: #0066cc;">📊 Will show <b>ALL WAREHOUSES COMBINED</b></span>'
#             elif count == 1:
#                 name = record.analytic_account_ids[0].name
#                 info = f'<span style="color: #28a745;">📋 Will show <b>{name} ONLY</b> (Separate Report)</span>'
#             else:
#                 info = f'<span style="color: #ff6600;">📦 Will show <b>{count} WAREHOUSES COMBINED</b> (with optional breakdown)</span>'
#             record.warehouse_selection_info = info
#
#     @api.onchange('analytic_account_ids')
#     def _onchange_analytic_account_ids(self):
#         """Auto-disable combined column when only one analytic is selected"""
#         if len(self.analytic_account_ids) <= 1:
#             self.include_combined = False
#
#     def _build_contexts(self, data):
#         """Override to add analytic account context"""
#         result = super(AccountingReport, self)._build_contexts(data)
#
#         # Add analytic account IDs to context
#         analytic_ids = []
#         form_data = data.get('form', {})
#         analytic_data = form_data.get('analytic_account_ids', [])
#
#         # Handle different formats of many2many field
#         if analytic_data:
#             if isinstance(analytic_data, (list, tuple)) and analytic_data:
#                 if isinstance(analytic_data[0], (list, tuple)):
#                     # Format: [(6, 0, [ids])]
#                     analytic_ids = analytic_data[0][2] if len(analytic_data[0]) > 2 else []
#                 else:
#                     # Format: [id1, id2, ...]
#                     analytic_ids = list(analytic_data)
#
#         result['analytic_account_ids'] = analytic_ids
#         result['include_combined'] = form_data.get('include_combined', False)
#
#         return result
#
#     def _build_comparison_context(self, data):
#         """Override to add analytic account context for comparison"""
#         result = super(AccountingReport, self)._build_comparison_context(data)
#
#         # Add analytic account IDs to context
#         analytic_ids = []
#         form_data = data.get('form', {})
#         analytic_data = form_data.get('analytic_account_ids', [])
#
#         # Handle different formats of many2many field
#         if analytic_data:
#             if isinstance(analytic_data, (list, tuple)) and analytic_data:
#                 if isinstance(analytic_data[0], (list, tuple)):
#                     # Format: [(6, 0, [ids])]
#                     analytic_ids = analytic_data[0][2] if len(analytic_data[0]) > 2 else []
#                 else:
#                     # Format: [id1, id2, ...]
#                     analytic_ids = list(analytic_data)
#
#         result['analytic_account_ids'] = analytic_ids
#         result['include_combined'] = form_data.get('include_combined', False)
#
#         return result
#
#     def check_report(self):
#         """Override to inject analytic data into the report"""
#         self.ensure_one()
#
#         # Get all parent fields first
#         parent_fields = [
#             'date_from_cmp', 'debit_credit', 'date_to_cmp',
#             'filter_cmp', 'account_report_id', 'enable_filter',
#             'label_filter', 'target_move', 'date_from', 'date_to',
#             'journal_ids', 'company_id'
#         ]
#
#         # Add our custom fields
#         all_fields = parent_fields + ['analytic_account_ids', 'include_combined']
#
#         # Prepare data dictionary
#         data = {}
#         data['ids'] = self.env.context.get('active_ids', [])
#         data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
#
#         # Read all fields
#         form_data = self.read(all_fields)[0]
#         data['form'] = form_data
#
#         # Ensure analytic_account_ids is in the proper format
#         if self.analytic_account_ids:
#             data['form']['analytic_account_ids'] = [(6, 0, self.analytic_account_ids.ids)]
#         else:
#             data['form']['analytic_account_ids'] = []
#
#         data['form']['include_combined'] = self.include_combined
#
#         # Build contexts with analytic filter
#         for field in ['date_from_cmp', 'date_to_cmp', 'date_from', 'date_to']:
#             if field in data['form'] and data['form'][field]:
#                 if isinstance(data['form'][field], tuple):
#                     data['form'][field] = data['form'][field][0]
#
#         # Build the used context with analytic filtering
#         used_context = self._build_contexts(data)
#         data['form']['used_context'] = used_context
#
#         # Get the comparison context
#         comparison_context = self._build_comparison_context(data)
#         data['form']['comparison_context'] = comparison_context
#
#         # Get the report action with context
#         return self.env.ref('accounting_pdf_reports.action_report_financial').with_context(
#             **used_context
#         ).report_action(self, data=data, config=False)
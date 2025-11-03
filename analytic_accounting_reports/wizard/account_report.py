# # -*- coding: utf-8 -*-
# from odoo import api, fields, models
#
#
# def _normalize_m2m_field(value):
#     """Return list of ids from possible many2many form formats:
#        - [(6, 0, [id1, id2])]
#        - [id1, id2]
#     """
#     if not value:
#         return []
#     if isinstance(value, (list, tuple)) and value and isinstance(value[0], (list, tuple)):
#         return value[0][2] if len(value[0]) > 2 else []
#     if isinstance(value, (list, tuple)):
#         return list(value)
#     return [value]
#
#
# class AccountingReport(models.TransientModel):
#     _inherit = "accounting.report"
#
#     # ------------------------------------------------------------------
#     #  ANALYTIC FILTER FIELDS
#     # ------------------------------------------------------------------
#     analytic_filter = fields.Selection(
#         [
#             ('all', 'All Analytic Accounts'),
#             ('selected', 'Selected Analytic Accounts'),
#         ],
#         string="Analytic Filter",
#         default='all'
#     )
#
#     analytic_account_ids = fields.Many2many(
#         'account.analytic.account',
#         string="Analytic Accounts"
#     )
#
#     show_analytic_breakdown = fields.Boolean(
#         string="Show Breakdown by Analytic",
#         help="If enabled, the report will split balances by analytic accounts."
#     )
#
#     include_combined = fields.Boolean(
#         string='Show Combined Column',
#         default=False,
#         help='Show total column when multiple analytic accounts are selected.'
#     )
#
#     # ------------------------------------------------------------------
#     #  ONCHANGE
#     # ------------------------------------------------------------------
#     @api.onchange('analytic_account_ids')
#     def _onchange_analytic_account_ids(self):
#         """Disable combined column when only one analytic is selected."""
#         if len(self.analytic_account_ids) <= 1:
#             self.include_combined = False
#
#     # ------------------------------------------------------------------
#     #  CONTEXT BUILDERS
#     # ------------------------------------------------------------------
#     def _build_contexts(self, data):
#         result = super()._build_contexts(data)
#         analytic_field = data.get('form', {}).get('analytic_account_ids', [])
#         result['analytic_account_ids'] = _normalize_m2m_field(analytic_field)
#         result['include_combined'] = data['form'].get('include_combined', False)
#         return result
#
#     def _build_comparison_context(self, data):
#         result = super()._build_comparison_context(data)
#         analytic_field = data.get('form', {}).get('analytic_account_ids', [])
#         result['analytic_account_ids'] = _normalize_m2m_field(analytic_field)
#         result['include_combined'] = data['form'].get('include_combined', False)
#         return result
#
#     # ------------------------------------------------------------------
#     #  REPORT ACTION
#     # ------------------------------------------------------------------
#     def _print_report(self, data):
#         """Inject analytic fields into report action."""
#         try:
#             vals = self.read([
#                 'date_from_cmp', 'debit_credit', 'date_to_cmp', 'filter_cmp',
#                 'account_report_id', 'enable_filter', 'label_filter', 'target_move',
#             ])[0]
#             data['form'].update(vals)
#         except Exception:
#             pass
#
#         data['form'].update({
#             'analytic_account_ids': [(6, 0, self.analytic_account_ids.ids)],
#             'include_combined': bool(self.include_combined),
#         })
#
#         return self.env.ref(
#             'accounting_pdf_reports.action_report_financial'
#         ).report_action(self, data=data, config=False)


# -*- coding: utf-8 -*-
# second code only get the combined data
# from odoo import api, fields, models
#
#
# class AccountingReport(models.TransientModel):
#     _inherit = "accounting.report"
#
#     analytic_filter = fields.Selection(
#         [
#             ('none', 'No Filter'),
#             ('warehouse', 'By Warehouse'),
#             ('analytic_account', 'By Analytic Account')
#         ],
#         string='Analytic Filter',
#         default='none'
#     )
#
#     # Analytic filter fields
#     analytic_account_ids = fields.Many2many(
#         'account.analytic.account',
#         string="Warehouses / Analytic Accounts",
#         help="Select specific warehouses/analytic accounts for filtering. "
#              "Leave empty to include all."
#     )
#
#     include_combined = fields.Boolean(
#         string='Show Combined Column',
#         default=False,
#         help='Show a combined total column when multiple analytic accounts are selected.'
#     )
#
#     show_warehouse_breakdown = fields.Boolean(
#         string='Show Warehouse Breakdown',
#         compute='_compute_show_breakdown',
#         store=False,
#         help='Shows breakdown by warehouse when multiple are selected.'
#     )
#
#     @api.depends('analytic_account_ids')
#     def _compute_show_breakdown(self):
#         """Compute whether to show warehouse breakdown"""
#         for record in self:
#             record.show_warehouse_breakdown = len(record.analytic_account_ids) > 1
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
#         # Prepare data dictionary
#         data = {}
#         data['ids'] = self.env.context.get('active_ids', [])
#         data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
#         data['form'] = self.read([
#             'date_from_cmp', 'debit_credit', 'date_to_cmp',
#             'filter_cmp', 'account_report_id', 'enable_filter',
#             'label_filter', 'target_move', 'date_from', 'date_to',
#             'journal_ids', 'analytic_account_ids', 'include_combined'
#         ])[0]
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
#             if data['form'][field]:
#                 if isinstance(data['form'][field], tuple):
#                     data['form'][field] = data['form'][field][0]
#
#         # Get the comparison context
#         comparison_context = self._build_comparison_context(data)
#         data['form']['comparison_context'] = comparison_context
#
#         # Get the report action
#         return self.env.ref('accounting_pdf_reports.action_report_financial').report_action(
#             self, data=data, config=False
#         )


# -*- coding: utf-8 -*-
#third code for check the separate datas
from odoo import api, fields, models


class AccountingReport(models.TransientModel):
    _inherit = "accounting.report"

    # Analytic filter fields
    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        string="Warehouses / Analytic Accounts",
        help="Select specific warehouses/analytic accounts for filtering.\n"
             "• Leave empty: Show all warehouses combined\n"
             "• Select ONE: Show only that warehouse (separate report)\n"
             "• Select MULTIPLE: Show combined with optional breakdown"
    )

    include_combined = fields.Boolean(
        string='Show Combined Column',
        default=False,
        help='Show a combined total column when multiple analytic accounts are selected.'
    )

    show_warehouse_breakdown = fields.Boolean(
        string='Show Warehouse Breakdown',
        compute='_compute_show_breakdown',
        store=False,
        help='Shows breakdown by warehouse when multiple are selected.'
    )

    warehouse_selection_info = fields.Html(
        string='Selection Info',
        compute='_compute_warehouse_info',
        store=False
    )

    @api.depends('analytic_account_ids')
    def _compute_show_breakdown(self):
        """Compute whether to show warehouse breakdown"""
        for record in self:
            record.show_warehouse_breakdown = len(record.analytic_account_ids) > 1

    @api.depends('analytic_account_ids')
    def _compute_warehouse_info(self):
        """Show helpful info about what report will be generated"""
        for record in self:
            count = len(record.analytic_account_ids)
            if count == 0:
                info = '<span style="color: #0066cc;">📊 Will show <b>ALL WAREHOUSES COMBINED</b></span>'
            elif count == 1:
                name = record.analytic_account_ids[0].name
                info = f'<span style="color: #28a745;">📋 Will show <b>{name} ONLY</b> (Separate Report)</span>'
            else:
                info = f'<span style="color: #ff6600;">📦 Will show <b>{count} WAREHOUSES COMBINED</b> (with optional breakdown)</span>'
            record.warehouse_selection_info = info

    @api.onchange('analytic_account_ids')
    def _onchange_analytic_account_ids(self):
        """Auto-disable combined column when only one analytic is selected"""
        if len(self.analytic_account_ids) <= 1:
            self.include_combined = False

    def _build_contexts(self, data):
        """Override to add analytic account context"""
        result = super(AccountingReport, self)._build_contexts(data)

        # Add analytic account IDs to context
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
        result = super(AccountingReport, self)._build_comparison_context(data)

        # Add analytic account IDs to context
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

    def check_report(self):
        """Override to inject analytic data into the report"""
        self.ensure_one()

        # Prepare data dictionary
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read([
            'date_from_cmp', 'debit_credit', 'date_to_cmp',
            'filter_cmp', 'account_report_id', 'enable_filter',
            'label_filter', 'target_move', 'date_from', 'date_to',
            'journal_ids', 'analytic_account_ids', 'include_combined'
        ])[0]

        # Ensure analytic_account_ids is in the proper format
        if self.analytic_account_ids:
            data['form']['analytic_account_ids'] = [(6, 0, self.analytic_account_ids.ids)]
        else:
            data['form']['analytic_account_ids'] = []

        data['form']['include_combined'] = self.include_combined

        # Build contexts with analytic filter
        for field in ['date_from_cmp', 'date_to_cmp', 'date_from', 'date_to']:
            if data['form'][field]:
                if isinstance(data['form'][field], tuple):
                    data['form'][field] = data['form'][field][0]

        # Get the comparison context
        comparison_context = self._build_comparison_context(data)
        data['form']['comparison_context'] = comparison_context

        # Get the report action
        return self.env.ref('accounting_pdf_reports.action_report_financial').report_action(
            self, data=data, config=False
        )
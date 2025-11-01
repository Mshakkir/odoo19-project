from odoo import api, fields, models


class AccountingReport(models.TransientModel):
    _inherit = "accounting.report"

    # Many2many field for selecting multiple warehouses
    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        'accounting_report_analytic_rel',
        'report_id',
        'analytic_id',
        string='Warehouses',
        help='Select one or more warehouses. Leave empty to include all warehouses.'
    )

    include_combined = fields.Boolean(
        string='Show Combined Column',
        default=False,
        help='When multiple warehouses are selected, show a combined total column'
    )

    @api.onchange('analytic_account_ids')
    def _onchange_analytic_account_ids(self):
        """Show/hide combined column option based on selection"""
        if len(self.analytic_account_ids) <= 1:
            self.include_combined = False

    def _build_contexts(self, data):
        """Override to add analytic context"""
        result = super(AccountingReport, self)._build_contexts(data)

        # Add analytic account IDs to context
        analytic_ids = data['form'].get('analytic_account_ids', [])
        if analytic_ids:
            # Handle tuple format from form: [(6, 0, [id1, id2, id3])]
            if analytic_ids and isinstance(analytic_ids[0], (list, tuple)):
                analytic_ids = analytic_ids[0][2] if len(analytic_ids[0]) > 2 else []
            result['analytic_account_ids'] = analytic_ids

        result['include_combined'] = data['form'].get('include_combined', False)

        return result

    def _build_comparison_context(self, data):
        """Override to add analytic context to comparison"""
        result = super(AccountingReport, self)._build_comparison_context(data)

        # Add analytic account IDs to comparison context
        analytic_ids = data['form'].get('analytic_account_ids', [])
        if analytic_ids:
            if analytic_ids and isinstance(analytic_ids[0], (list, tuple)):
                analytic_ids = analytic_ids[0][2] if len(analytic_ids[0]) > 2 else []
            result['analytic_account_ids'] = analytic_ids

        result['include_combined'] = data['form'].get('include_combined', False)

        return result

    def _print_report(self, data):
        """Override to pass analytic fields"""
        data['form'].update(self.read([
            'date_from_cmp', 'debit_credit', 'date_to_cmp', 'filter_cmp',
            'account_report_id', 'enable_filter', 'label_filter', 'target_move',
            'analytic_account_ids', 'include_combined'
        ])[0])
        return self.env.ref('accounting_pdf_reports.action_report_financial').report_action(
            self, data=data, config=False)
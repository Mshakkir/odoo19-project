from odoo import api, fields, models


class AccountingReport(models.TransientModel):
    _inherit = "accounting.report"

    # Add analytic account filtering fields
    analytic_filter = fields.Selection([
        ('all', 'All Warehouses Combined'),
        ('baladiya', 'SSAQCO - Baladiya'),
        ('dammam', 'SSAQCO - Dammam'),
        ('mainoffice', 'SSAQCO - Main Office'),
    ], string='Warehouse Selection', default='all', required=True)

    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Warehouse/Analytic Account',
        help='Select specific warehouse for filtered report'
    )

    show_analytic_breakdown = fields.Boolean(
        string='Show Warehouse Breakdown',
        help='Display separate columns for each warehouse (Only for All Warehouses Combined)'
    )

    @api.onchange('analytic_filter')
    def _onchange_analytic_filter(self):
        """Clear analytic account when filter changes to 'all'"""
        if self.analytic_filter == 'all':
            self.analytic_account_id = False
            self.show_analytic_breakdown = False

    def _build_contexts(self, data):
        """Override to add analytic context"""
        result = super(AccountingReport, self)._build_contexts(data)

        # Add analytic filtering to context
        if data['form'].get('analytic_filter') == 'specific' and data['form'].get('analytic_account_id'):
            analytic_id = data['form']['analytic_account_id']
            if isinstance(analytic_id, tuple):
                analytic_id = analytic_id[0]
            result['analytic_account_id'] = analytic_id

        result['show_analytic_breakdown'] = data['form'].get('show_analytic_breakdown', False)

        return result

    def _build_comparison_context(self, data):
        """Override to add analytic context to comparison"""
        result = super(AccountingReport, self)._build_comparison_context(data)

        if data['form'].get('analytic_filter') == 'specific' and data['form'].get('analytic_account_id'):
            analytic_id = data['form']['analytic_account_id']
            if isinstance(analytic_id, tuple):
                analytic_id = analytic_id[0]
            result['analytic_account_id'] = analytic_id

        result['show_analytic_breakdown'] = data['form'].get('show_analytic_breakdown', False)

        return result

    def _print_report(self, data):
        """Override to pass analytic fields"""
        data['form'].update(self.read([
            'date_from_cmp', 'debit_credit', 'date_to_cmp', 'filter_cmp',
            'account_report_id', 'enable_filter', 'label_filter', 'target_move',
            'analytic_filter', 'analytic_account_id', 'show_analytic_breakdown'
        ])[0])
        return self.env.ref('accounting_pdf_reports.action_report_financial').report_action(
            self, data=data, config=False)